"""Citation relevance filtering and RAG extractive helpers for LegalMitra research."""

from __future__ import annotations

import logging
import re
from typing import Any

_logger = logging.getLogger(__name__)

_LEGAL_QUERY_WORD_RE = re.compile(r"[a-z0-9]+")
_LEGAL_QUERY_STOPWORDS = {
    "what", "which", "when", "where", "who", "whom", "whose",
    "why", "how", "is", "are", "was", "were", "do", "does",
    "did", "can", "could", "should", "would", "please", "explain",
    "briefly", "about", "tell", "me", "the", "for", "and", "with",
    "a", "an", "of", "in", "on", "to", "by", "as", "or", "if",
    "this", "that", "these", "those", "be", "been", "being",
    "have", "has", "had", "from", "any", "all", "there", "here",
    "under", "over", "into", "per", "via", "than", "then",
}

_SECTION_IN_QUERY_RE = re.compile(
    r"(?:section|sec\.?|§)\s*(\d+[A-Za-z]?)|"
    r"\bs\.?\s*(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)


def extract_meaningful_query_terms(query: str) -> set[str]:
    tokens = set(_LEGAL_QUERY_WORD_RE.findall((query or "").lower()))
    return {t for t in tokens if len(t) >= 4 and t not in _LEGAL_QUERY_STOPWORDS}


def citation_is_relevant(
    citation: dict[str, Any], query_terms: set[str]
) -> tuple[bool, int, float]:
    """Return (relevant, overlap_count, overlap_ratio) for a single citation.

    Relevance rule: at least 2 meaningful query terms must appear in the citation's
    snippet/title/legal-metadata/reference, OR at least 30% of meaningful terms
    overlap.

    If the citation exposes no inspectable content, treat as relevant (stubs in tests).
    """
    if not query_terms:
        return (True, 0, 1.0)

    haystack_parts: list[str] = []
    for key in ("snippet", "title", "reference", "text"):
        val = citation.get(key)
        if val:
            haystack_parts.append(str(val))
    legal_meta = citation.get("legal_metadata") or {}
    if isinstance(legal_meta, dict):
        for val in legal_meta.values():
            if val:
                haystack_parts.append(str(val))

    haystack = " ".join(haystack_parts).lower().strip()
    if not haystack:
        return (True, 0, 1.0)

    haystack_tokens = set(_LEGAL_QUERY_WORD_RE.findall(haystack))
    hits = query_terms.intersection(haystack_tokens)
    ratio = len(hits) / max(len(query_terms), 1)

    relevant = len(hits) >= 2 or ratio >= 0.30
    return (relevant, len(hits), ratio)


def section_tokens_in_query(query: str) -> set[str]:
    found: set[str] = set()
    for match in _SECTION_IN_QUERY_RE.finditer(query or ""):
        token = (match.group(1) or match.group(2) or "").strip().upper()
        if token:
            found.add(token)
    return found


def citation_mentions_section(citation: dict[str, Any], sections: set[str]) -> bool:
    if not sections:
        return False
    parts: list[str] = []
    for key in ("snippet", "title", "reference", "text"):
        val = citation.get(key)
        if val:
            parts.append(str(val))
    legal_meta = citation.get("legal_metadata") or {}
    if isinstance(legal_meta, dict):
        for key in ("section", "act", "act_name", "citation", "title"):
            val = legal_meta.get(key)
            if val:
                parts.append(str(val))
        meta_section = str(legal_meta.get("section") or "").strip().upper()
        if meta_section in sections:
            return True
    blob = " ".join(parts)
    for section in sections:
        if re.search(
            rf"(?:section|sec\.?|§|s\.)\s*{re.escape(section)}\b",
            blob,
            re.IGNORECASE,
        ):
            return True
    return False


def recover_section_matched_citations(
    citations: list[dict[str, Any]], query: str
) -> list[dict[str, Any]]:
    """When the term filter drops all hits, keep chunks that cite the queried section."""
    sections = section_tokens_in_query(query)
    if not sections:
        return []
    return [
        c
        for c in citations
        if isinstance(c, dict) and citation_mentions_section(c, sections)
    ]


def filter_citations_by_relevance(
    citations: list[dict[str, Any]], query: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split citations into (relevant, dropped)."""
    query_terms = extract_meaningful_query_terms(query)
    if not query_terms:
        return (list(citations), [])

    relevant: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for c in citations:
        is_rel, hits, ratio = citation_is_relevant(c, query_terms)
        if is_rel:
            relevant.append(c)
        else:
            _logger.debug(
                "citation_dropped title=%r hits=%d ratio=%.2f",
                c.get("title") or c.get("reference") or "?",
                hits,
                ratio,
            )
            dropped.append(c)

    if not relevant and citations:
        recovered = recover_section_matched_citations(citations, query)
        if recovered:
            _logger.info(
                "citation_recovery section_match recovered=%d of=%d query_sections=%s",
                len(recovered),
                len(citations),
                sorted(section_tokens_in_query(query)),
            )
            recovered_ids = {id(c) for c in recovered}
            return (recovered, [c for c in citations if id(c) not in recovered_ids])

    return (relevant, dropped)


def rag_extractive_answer_usable(rag_result: dict[str, Any]) -> str | None:
    """Return RAG extractive answer text when it is source-backed and not an empty-corpus stub."""
    answer = str(rag_result.get("answer") or "").strip()
    if not answer:
        return None
    lowered = answer.lower()
    if "do not have enough indexed content" in lowered:
        return None
    if "no matching" in lowered and "knowledge" in lowered:
        return None
    return answer


async def query_rag_for_legal_research(
    *,
    tenant_id: str,
    app_key: str,
    query: str,
    enabled: bool,
) -> dict[str, Any]:
    """Run tenant-scoped RAG for /legal-research, or return a disabled/unavailable stub."""
    if not enabled:
        return {
            "answer": "",
            "citations": [],
            "strategy": "rag_disabled",
            "candidate_count": 0,
            "context": None,
        }

    from app.modules.rag.schemas import RagQueryRequest
    from app.modules.rag.service import query_knowledge

    rag_payload = RagQueryRequest(
        query=query,
        top_k=5,
        max_candidates=300,
        include_context=False,
    )
    try:
        return await query_knowledge(
            tenant_id=tenant_id, app_key=app_key, payload=rag_payload
        )
    except Exception as exc:
        _logger.warning(
            "legal_research rag_query failed tenant=%s app=%s err=%s",
            tenant_id,
            app_key,
            type(exc).__name__,
            exc_info=True,
        )
        return {
            "answer": "",
            "citations": [],
            "strategy": "rag_unavailable",
            "candidate_count": 0,
            "context": None,
        }
