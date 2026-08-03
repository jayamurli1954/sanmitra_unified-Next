"""Stage 5 step adapters — deterministic service helpers, not autonomous agents.

Research never invents statutes. Drafts always require human review.
Knowledge graph is reserved as optional enrichment only (not primary SoT).
"""
from __future__ import annotations

from typing import Any

from app.modules.legal.practice_service import (
    get_matter,
    list_matter_documents,
    list_matter_timeline,
)
from app.modules.legal import extract_service
from app.modules.legal.workflow_definitions import (
    TEMPLATE_DOC_CHECKLIST,
    TEMPLATE_QUERY_SEEDS,
    resolve_template,
)

ADVISORY = (
    "Advisory working product only. Not final legal advice. "
    "A qualified professional must review before filing or advising a client."
)


async def adapter_matter_intake(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    workflow_template: str,
) -> dict[str, Any]:
    matter = await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    missing = []
    if not matter.get("jurisdiction"):
        missing.append("jurisdiction")
    if not matter.get("next_deadline_date") and not matter.get("next_hearing_date"):
        missing.append("next_deadline_or_hearing_date")
    payload = {
        "matter_id": matter_id,
        "matter_number": matter.get("matter_number"),
        "title": matter.get("title"),
        "status": matter.get("status"),
        "practice_area": matter.get("practice_area"),
        "jurisdiction": matter.get("jurisdiction"),
        "court": matter.get("court"),
        "next_deadline_date": (
            matter["next_deadline_date"].isoformat()
            if hasattr(matter.get("next_deadline_date"), "isoformat")
            else matter.get("next_deadline_date")
        ),
        "next_hearing_date": (
            matter["next_hearing_date"].isoformat()
            if hasattr(matter.get("next_hearing_date"), "isoformat")
            else matter.get("next_hearing_date")
        ),
        "workflow_template": resolve_template(workflow_template),
        "intake_gaps": missing,
        "advisory_notice": ADVISORY,
    }
    confidence = 0.9 if not missing else 0.7
    return {
        "artifact_type": "note",
        "payload": payload,
        "sources": [{"source_type": "matter_record", "matter_id": matter_id}],
        "confidence": confidence,
        "human_review_required": False,
        "failure_class": None,
    }


async def adapter_legal_research(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    workflow_template: str,
) -> dict[str, Any]:
    """Grounded research pack from matter context — does not invent citations."""
    matter = await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    template = resolve_template(workflow_template)
    seed = TEMPLATE_QUERY_SEEDS.get(template, TEMPLATE_QUERY_SEEDS["general"])
    query = (
        f"{seed} Matter: {matter.get('matter_number')} — {matter.get('title')}. "
        f"Practice area: {matter.get('practice_area') or 'general'}. "
        f"Jurisdiction: {matter.get('jurisdiction') or 'not specified'}."
    )
    sources: list[dict[str, Any]] = [
        {"source_type": "matter_record", "matter_id": matter_id}
    ]
    docs = await list_matter_documents(
        tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=20
    )
    for doc in docs:
        sources.append(
            {
                "source_type": "matter_document",
                "document_id": doc.get("document_id"),
                "filename": doc.get("filename"),
            }
        )
    chunks = await extract_service.list_matter_chunks(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        approved_only=True,
        limit=20,
    )
    for chunk in chunks:
        sources.append(
            {
                "source_type": "matter_paper_chunk",
                "source_kind": chunk.get("source_kind") or "matter_paper",
                "chunk_id": chunk.get("chunk_id"),
                "extract_id": chunk.get("extract_id"),
                "document_id": chunk.get("document_id"),
            }
        )

    # Stage 5 MVP: matter-grounded research brief. No fabricated statute citations.
    # Optional KG enrichment hook reserved — graph miss degrades to this path.
    jurisdiction = matter.get("jurisdiction")
    if not jurisdiction:
        payload = {
            "strategy": "insufficient_sources",
            "question": query,
            "answer": (
                "Research step refused to generate legal analysis without an explicit "
                "jurisdiction on the matter. Record jurisdiction, then retry or use "
                "LegalMitra research with citations."
            ),
            "citations": [],
            "confidence": 0.2,
            "human_review_required": True,
            "advisory_notice": ADVISORY,
            "limitations": [
                "Jurisdiction missing on matter record.",
                "Never invent hearings, statutes, or court dates.",
            ],
            "suggested_research_query": query,
            "kg_enrichment_used": False,
        }
        return {
            "artifact_type": "research_response",
            "payload": payload,
            "sources": sources,
            "confidence": 0.2,
            "human_review_required": True,
            "failure_class": "requires_human",
            "error": "Jurisdiction required before research can proceed",
            "force_awaiting_human": True,
        }

    extract_facts = [
        f"Approved extract ({c.get('document_id')}): {str(c.get('text') or '')[:220]}"
        for c in chunks[:5]
        if c.get("text")
    ]
    payload = {
        "strategy": "grounded_matter_research_brief",
        "question": query,
        "answer": (
            f"Working research brief for {matter.get('matter_number')}: {matter.get('title')}. "
            f"Grounded on case card"
            + (f" and {len(chunks)} approved matter-paper chunk(s)" if chunks else "")
            + ". Use LegalMitra hybrid research on the suggested query to obtain statute/case "
            "citations. This Stage 5 step does not invent legal authorities."
        ),
        "key_facts": [
            f"Matter number: {matter.get('matter_number')}",
            f"Status: {matter.get('status')}",
            f"Practice area: {matter.get('practice_area') or 'general'}",
            f"Jurisdiction: {jurisdiction}",
            *extract_facts,
        ],
        "citations": [],
        "confidence": 0.65 if chunks else (0.55 if docs else 0.45),
        "human_review_required": True,
        "advisory_notice": ADVISORY,
        "limitations": [
            "No statute or case citations were fabricated in this step.",
            "Run LegalMitra research (Stage 2) for grounded citations before filing.",
            "Knowledge graph enrichment is optional and was not required for this brief.",
            (
                "Matter-paper extracts were used with document attribution."
                if chunks
                else "No approved matter-paper extracts yet — research is case-card/filename grounded only."
            ),
        ],
        "suggested_research_query": query,
        "suggested_next_actions": [
            "Run hybrid legal research with the suggested query",
            "Attach any missing source documents",
            "Approve this research step only after verifying authorities",
        ],
        "kg_enrichment_used": False,
        "matter_paper_chunk_count": len(chunks),
    }
    return {
        "artifact_type": "research_response",
        "payload": payload,
        "sources": sources,
        "confidence": payload["confidence"],
        "human_review_required": True,
        "failure_class": None,
    }


async def adapter_document_evidence(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    workflow_template: str,
) -> dict[str, Any]:
    matter = await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    template = resolve_template(workflow_template)
    checklist = list(TEMPLATE_DOC_CHECKLIST.get(template, TEMPLATE_DOC_CHECKLIST["general"]))
    docs = await list_matter_documents(
        tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=50
    )
    chunks = await extract_service.list_matter_chunks(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        approved_only=True,
        limit=40,
    )
    filenames = " ".join(str(d.get("filename") or "").lower() for d in docs)
    extract_blob = " ".join(str(c.get("text") or "").lower() for c in chunks)
    present = []
    missing = []
    for item in checklist:
        token = item.split()[0].lower()
        in_filename = any(token in str(d.get("filename") or "").lower() for d in docs) or (
            docs and item.lower() in filenames
        )
        in_extract = bool(chunks) and (
            token in extract_blob or item.lower() in extract_blob
        )
        if in_filename or in_extract:
            present.append(item)
        else:
            # Heuristic: if docs exist, mark generic items present only when filenames match.
            if docs and item in {"Client instructions", "Key evidence", "Supporting accounts"}:
                present.append(item)
            else:
                missing.append(item)

    payload = {
        "matter_id": matter_id,
        "matter_number": matter.get("matter_number"),
        "workflow_template": template,
        "checklist": checklist,
        "documents_attached": [
            {"document_id": d.get("document_id"), "filename": d.get("filename")}
            for d in docs
        ],
        "approved_extract_snippets": [
            {
                "chunk_id": c.get("chunk_id"),
                "document_id": c.get("document_id"),
                "extract_id": c.get("extract_id"),
                "text": str(c.get("text") or "")[:240],
            }
            for c in chunks[:8]
        ],
        "present": present,
        "missing": missing,
        "advisory_notice": ADVISORY,
    }
    confidence = 1.0 if not missing else max(0.4, 1.0 - 0.15 * len(missing))
    if chunks:
        confidence = min(1.0, confidence + 0.05)
    sources = [
        {"source_type": "matter_document", "document_id": d.get("document_id")}
        for d in docs
    ]
    sources.extend(
        {
            "source_type": "matter_paper_chunk",
            "chunk_id": c.get("chunk_id"),
            "document_id": c.get("document_id"),
            "extract_id": c.get("extract_id"),
        }
        for c in chunks
    )
    return {
        "artifact_type": "checklist",
        "payload": payload,
        "sources": sources,
        "confidence": round(confidence, 2),
        "human_review_required": False,
        "failure_class": None,
    }


async def adapter_drafting(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    workflow_template: str,
    prior_artifacts: list[dict],
) -> dict[str, Any]:
    matter = await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    template = resolve_template(workflow_template)
    research = next(
        (
            a
            for a in reversed(prior_artifacts)
            if a.get("artifact_type") == "research_response"
        ),
        None,
    )
    checklist = next(
        (a for a in reversed(prior_artifacts) if a.get("artifact_type") == "checklist"),
        None,
    )
    missing = (checklist or {}).get("payload", {}).get("missing") or []
    extract_snips = (checklist or {}).get("payload", {}).get("approved_extract_snippets") or []
    if not extract_snips:
        chunks = await extract_service.list_matter_chunks(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            approved_only=True,
            limit=8,
        )
        extract_snips = [
            {
                "chunk_id": c.get("chunk_id"),
                "document_id": c.get("document_id"),
                "extract_id": c.get("extract_id"),
                "text": str(c.get("text") or "")[:240],
            }
            for c in chunks
        ]
    draft_body = [
        f"# Draft outline — {matter.get('matter_number')} ({template})",
        "",
        f"**Matter:** {matter.get('title')}",
        f"**Client:** {matter.get('client_name') or matter.get('client_id')}",
        f"**Jurisdiction:** {matter.get('jurisdiction') or '[confirm]'}",
        "",
        "## Working structure",
        "1. Facts as recorded on the matter file",
        "2. Issues for determination (confirm after research approval)",
        "3. Legal submissions — insert only verified Stage 2 citations",
        "4. Prayer / relief sought",
        "5. Annexure list from evidence checklist",
        "",
        "## Approved matter-paper extracts (attribution required)",
    ]
    if extract_snips:
        for snip in extract_snips[:6]:
            draft_body.append(
                f"- [doc {snip.get('document_id')}] {snip.get('text')}"
            )
    else:
        draft_body.append(
            "- No approved extracts yet — paste extracts in Tracker before relying on paper text."
        )
    draft_body.extend(
        [
            "",
            "## Evidence gaps to resolve before filing",
        ]
    )
    if missing:
        draft_body.extend(f"- {item}" for item in missing)
    else:
        draft_body.append("- No checklist gaps flagged (still verify originals).")
    draft_body.extend(
        [
            "",
            "## Limitations",
            "- This is an advisory outline only.",
            "- Do not file or send without human review.",
            "- Do not invent statutes or case citations in this draft.",
        ]
    )
    if research:
        draft_body.append(
            f"- Research strategy noted: {(research.get('payload') or {}).get('strategy')}"
        )

    payload = {
        "title": f"Draft outline — {matter.get('matter_number')}",
        "body": "\n".join(draft_body),
        "workflow_template": template,
        "human_review_required": True,
        "advisory_notice": ADVISORY,
        "ready_to_file": False,
        "matter_paper_extract_count": len(extract_snips),
    }
    sources = [{"source_type": "matter_record", "matter_id": matter_id}]
    sources.extend(
        {
            "source_type": "matter_paper_chunk",
            "chunk_id": snip.get("chunk_id"),
            "document_id": snip.get("document_id"),
            "extract_id": snip.get("extract_id"),
        }
        for snip in extract_snips
    )
    return {
        "artifact_type": "draft",
        "payload": payload,
        "sources": sources,
        "confidence": 0.75 if extract_snips and not missing else (0.7 if not missing else 0.55),
        "human_review_required": True,
        "failure_class": None,
    }


async def adapter_human_review_gate(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    prior_artifacts: list[dict],
) -> dict[str, Any]:
    types = {a.get("artifact_type") for a in prior_artifacts}
    payload = {
        "matter_id": matter_id,
        "artifacts_present": sorted(t for t in types if t),
        "checklist": [
            "Research step human-approved",
            "Draft step human-approved",
            "No filing or client send from this workflow",
        ],
        "advisory_notice": ADVISORY,
        "human_review_required": True,
    }
    return {
        "artifact_type": "note",
        "payload": payload,
        "sources": [{"source_type": "workflow_run"}],
        "confidence": 1.0,
        "human_review_required": True,
        "failure_class": None,
    }


async def adapter_complete(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
) -> dict[str, Any]:
    timeline = await list_matter_timeline(
        tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=5
    )
    payload = {
        "matter_id": matter_id,
        "completed": True,
        "ready_to_file": False,
        "filed": False,
        "sent": False,
        "note": (
            "Workflow complete. Ready-to-file is a separate human marker and does not "
            "file or send anything."
        ),
        "recent_timeline_events": len(timeline),
        "advisory_notice": ADVISORY,
    }
    return {
        "artifact_type": "note",
        "payload": payload,
        "sources": [{"source_type": "matter_record", "matter_id": matter_id}],
        "confidence": 1.0,
        "human_review_required": False,
        "failure_class": None,
    }
