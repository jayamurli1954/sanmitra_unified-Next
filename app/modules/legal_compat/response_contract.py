"""LegalMitra Stage 2 research response contract helpers.

Enforces the fields defined in docs/architecture/LEGALMITRA_RAG_RESPONSE_CONTRACT.md
without inventing legal authority when retrieved sources are missing.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

ADVISORY_NOTICE = (
    "This output is draft/advisory only. It is not final legal advice. "
    "A qualified professional must review before filing, advising a client, or taking action."
)

_CONFIDENCE_VALUES = frozenset({"high", "medium", "low", "insufficient_sources"})

_JURISDICTION_MARKERS = (
    "india",
    "indian",
    "central",
    "union territory",
    "delhi",
    "maharashtra",
    "karnataka",
    "tamil nadu",
    "telangana",
    "andhra pradesh",
    "gujarat",
    "rajasthan",
    "west bengal",
    "uttar pradesh",
    "kerala",
    "punjab",
    "haryana",
    "madhya pradesh",
    "odisha",
    "bihar",
    "assam",
    "jharkhand",
    "chhattisgarh",
    "goa",
    "himachal",
    "uttarakhand",
)

_CENTRAL_TAX_MARKERS = (
    "gst",
    "cgst",
    "igst",
    "sgst",
    "utgst",
    "income tax",
    "income-tax",
    "it act",
    "section 54",
    "refund of tax",
)

_STATE_GST_MARKERS = (
    "state gst",
    "sgst rate",
    "state notification",
    "state amendment",
)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def enrich_citations(citations: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Ensure citation entries carry retrieval/staleness metadata."""
    enriched: list[dict[str, Any]] = []
    retrieved_at = _now_utc_iso()
    for index, citation in enumerate(citations or [], start=1):
        if not isinstance(citation, dict):
            continue
        item = dict(citation)
        item.setdefault("index", item.get("index") or index)
        item.setdefault("retrieved_at", retrieved_at)
        source_date = item.get("source_date") or (item.get("legal_metadata") or {}).get("document_date")
        if source_date and not item.get("source_date"):
            item["source_date"] = source_date
        item.setdefault(
            "staleness_status",
            "unknown" if not item.get("source_date") else item.get("staleness_status") or "possibly_stale",
        )
        if item.get("staleness_status") in {"unknown", "possibly_stale", "stale"} and not item.get(
            "source_currentness_note"
        ):
            item["source_currentness_note"] = (
                "Verify the current statutory text, notifications, and amendments before reliance."
            )
        enriched.append(item)
    return enriched


def infer_confidence(citations: list[dict[str, Any]] | None, *, forced: str | None = None) -> str:
    if forced and forced in _CONFIDENCE_VALUES:
        return forced
    count = len(citations or [])
    if count <= 0:
        return "insufficient_sources"
    if count >= 3:
        return "high"
    if count == 2:
        return "medium"
    return "low"


def _answer_summary_from_response(response: str) -> str:
    text = (response or "").strip()
    if not text:
        return ""
    # Prefer first non-heading paragraph.
    for block in re.split(r"\n\s*\n", text):
        cleaned = re.sub(r"^#+\s*", "", block.strip())
        cleaned = re.sub(r"^\*+", "", cleaned).strip()
        if cleaned and not cleaned.lower().startswith("disclaimer"):
            return cleaned[:400]
    return text[:400]


def resolve_jurisdiction(query: str) -> tuple[str | None, bool]:
    """Return (jurisdiction, missing_jurisdiction).

    Central GST / Income-tax questions safely infer India (Central).
    Explicit state-GST questions without a state/jurisdiction marker refuse.
    """
    q = " ".join((query or "").lower().split())
    if not q:
        return None, False

    mentioned = [marker for marker in _JURISDICTION_MARKERS if marker in q]
    is_central_tax = any(marker in q for marker in _CENTRAL_TAX_MARKERS)
    is_state_gst = any(marker in q for marker in _STATE_GST_MARKERS)

    if is_state_gst and not mentioned:
        return None, True

    if mentioned:
        if "india" in mentioned or "indian" in mentioned or "central" in mentioned:
            return "India (Central)", False
        # Prefer the first concrete state/UT-style marker.
        for marker in mentioned:
            if marker not in {"india", "indian", "central", "union territory"}:
                return marker.title(), False
        return "India (Central)", False

    if is_central_tax:
        return "India (Central)", False

    return None, False


def default_limitations(
    *,
    confidence: str,
    citations: list[dict[str, Any]],
    missing_jurisdiction: bool = False,
    extra: list[str] | None = None,
) -> list[str]:
    limitations: list[str] = []
    if missing_jurisdiction:
        limitations.append("Jurisdiction was not supplied for a jurisdiction-dependent question.")
    if confidence == "insufficient_sources" or not citations:
        limitations.append("No sufficient retrieved or authorized sources were available for citation-backed research.")
    else:
        limitations.append("Retrieved sources may be incomplete or not reflect the latest amendments.")
        if any(str(c.get("staleness_status") or "") in {"unknown", "possibly_stale", "stale"} for c in citations):
            limitations.append("One or more citations lack a confirmed current source date.")
    limitations.append("Facts specific to the matter were not verified against filings or primary documents.")
    for item in extra or []:
        if item and item not in limitations:
            limitations.append(item)
    return limitations


def finalize_research_response(
    *,
    question: str,
    response: str,
    citations: list[dict[str, Any]] | None,
    strategy: str,
    provider: str | None = None,
    note: str | None = None,
    dropped_citation_count: int = 0,
    jurisdiction: str | None = None,
    missing_jurisdiction: bool = False,
    confidence: str | None = None,
    limitations: list[str] | None = None,
    answer_summary: str | None = None,
    analysis: str | None = None,
) -> dict[str, Any]:
    enriched = enrich_citations(citations)
    resolved_confidence = infer_confidence(enriched, forced=confidence)
    summary = (answer_summary or _answer_summary_from_response(response)).strip()
    resolved_limitations = limitations or default_limitations(
        confidence=resolved_confidence,
        citations=enriched,
        missing_jurisdiction=missing_jurisdiction,
    )

    payload: dict[str, Any] = {
        # Backward-compatible primary body used by current LegalMitra UI.
        "response": response,
        "question": (question or "").strip(),
        "jurisdiction": jurisdiction,
        "missing_jurisdiction": bool(missing_jurisdiction),
        "answer_summary": summary,
        "analysis": analysis,
        "citations": enriched,
        "confidence": resolved_confidence,
        "limitations": resolved_limitations,
        "human_review_required": True,
        "advisory_notice": ADVISORY_NOTICE,
        "retrieval_strategy": strategy,
        "strategy": strategy,
        "provider": provider,
        "note": note,
        "dropped_citation_count": int(dropped_citation_count or 0),
        "generated_at": _now_utc_iso(),
    }
    return payload


def insufficient_sources_response(
    *,
    question: str,
    jurisdiction: str | None = None,
    dropped_citation_count: int = 0,
    note: str | None = None,
) -> dict[str, Any]:
    response = (
        "**Insufficient Sources**\n\n"
        "LegalMitra does not have enough retrieved or authorized sources to answer this "
        "question with citation-backed legal research.\n\n"
        "No statute sections, case names, or court references are invented when sources are missing.\n\n"
        "**Suggested next steps**\n"
        "- Narrow the query (for GST refunds: CGST Act Section 54 family)\n"
        "- Confirm jurisdiction when the issue is state-specific\n"
        "- Ingest or sync the relevant Act/notification materials and retry"
    )
    return finalize_research_response(
        question=question,
        response=response,
        citations=[],
        strategy="insufficient_sources",
        provider=None,
        note=note or "Refused uncited generation under LegalMitra Stage 2 response contract.",
        dropped_citation_count=dropped_citation_count,
        jurisdiction=jurisdiction,
        confidence="insufficient_sources",
        limitations=default_limitations(
            confidence="insufficient_sources",
            citations=[],
            missing_jurisdiction=False,
        ),
        answer_summary=(
            "Insufficient retrieved sources are available for citation-backed legal research; "
            "the system refused to invent authority."
        ),
    )


def missing_jurisdiction_response(*, question: str, dropped_citation_count: int = 0) -> dict[str, Any]:
    response = (
        "**Jurisdiction Required**\n\n"
        "This question appears jurisdiction-dependent. Specify the jurisdiction "
        "(for example: India / Central, or the relevant State for state GST issues) "
        "before LegalMitra continues research.\n\n"
        "No legal answer is generated until jurisdiction is supplied or safely inferred."
    )
    return finalize_research_response(
        question=question,
        response=response,
        citations=[],
        strategy="missing_jurisdiction",
        provider=None,
        note="Blocked pending jurisdiction under LegalMitra Stage 2 response contract.",
        dropped_citation_count=dropped_citation_count,
        jurisdiction=None,
        missing_jurisdiction=True,
        confidence="insufficient_sources",
        limitations=default_limitations(
            confidence="insufficient_sources",
            citations=[],
            missing_jurisdiction=True,
        ),
        answer_summary="Jurisdiction is required before citation-backed research can continue.",
    )
