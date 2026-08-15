"""Labeled non-research fallbacks for LegalMitra RAG query.

Uncited Gemini answers are opt-in via LEGAL_HYBRID_AI_FALLBACK_ENABLED (default off).
When enabled they must never be presented as source-backed legal research.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings

_logger = logging.getLogger(__name__)

GENERAL_KNOWLEDGE_BANNER = (
    "GENERAL KNOWLEDGE ONLY — not source-backed legal research. "
    "No retrieved citations. Do not treat named cases, sections, or holdings in this "
    "answer as verified authority. Human review is required."
)

WEB_SEARCH_BANNER = (
    "UNVERIFIED WEB SEARCH — not indexed LegalMitra research. "
    "Links below are live-web snippets, not retrieved RAG citations. "
    "Verify against the original source before filing or advising. Human review is required."
)

INSUFFICIENT_INDEX_ANSWER = (
    "I do not have enough indexed content to answer this question as source-backed "
    "legal research. Ingest relevant statutes or judgments, or narrow the query. "
    "LegalMitra will not invent case names, section numbers, or citations."
)

_GENERAL_KNOWLEDGE_PROMPT = (
    "You are LegalMitra. Local retrieved sources were insufficient.\n"
    "Answer from general knowledge of Indian law only.\n"
    "Do NOT invent case names, citations, section numbers, court holdings, or URLs.\n"
    "If you are unsure, say so. Do not claim this is research from a knowledge base.\n"
    "Keep the answer advisory; a qualified professional must review it.\n\n"
    "User question: {query}"
)


def log_rag_refusal(
    *,
    tenant_id: str,
    app_key: str,
    query: str,
    reason: str,
    strategy: str,
) -> None:
    _logger.info(
        "rag_refusal tenant=%s app=%s reason=%s strategy=%s query=%r",
        tenant_id,
        app_key,
        reason,
        strategy,
        (query or "")[:80],
    )


def insufficient_index_payload(
    *,
    strategy: str,
    candidate_count: int,
    include_context: bool,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "answer": INSUFFICIENT_INDEX_ANSWER,
        "citations": [],
        "strategy": strategy,
        "candidate_count": candidate_count,
        "context": [] if include_context else None,
        "is_fallback": False,
        "knowledge_kind": "insufficient_sources",
        "is_source_backed_research": False,
        "human_review_required": True,
        "advisory_notice": INSUFFICIENT_INDEX_ANSWER,
        "rejection_reason": reason,
    }
    if extra:
        payload.update(extra)
    return payload


def labeled_non_research_payload(
    *,
    answer: str,
    strategy: str,
    candidate_count: int,
    knowledge_kind: str,
    banner: str,
) -> dict[str, Any]:
    body = (answer or "").strip()
    labeled = f"{banner}\n\n{body}" if body else banner
    return {
        "answer": labeled,
        "citations": [],
        "strategy": strategy,
        "candidate_count": candidate_count,
        "context": None,
        "is_fallback": True,
        "knowledge_kind": knowledge_kind,
        "is_source_backed_research": False,
        "human_review_required": True,
        "advisory_notice": banner,
    }


def try_general_knowledge_llm(
    *,
    query: str,
    strategy: str,
    candidate_count: int,
) -> dict[str, Any] | None:
    """Return a labeled general-knowledge answer, or None when the opt-in flag is off."""
    settings = get_settings()
    if not settings.LEGAL_HYBRID_AI_FALLBACK_ENABLED:
        return None
    if not settings.GEMINI_API_KEY:
        _logger.info("general_knowledge_llm skipped: GEMINI_API_KEY missing")
        return None

    model = settings.LEGAL_FALLBACK_GEMINI_MODEL or "gemini-2.5-flash"
    api_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={settings.GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": _GENERAL_KNOWLEDGE_PROMPT.format(query=query)}]}],
        "generationConfig": {
            "maxOutputTokens": settings.LEGAL_FALLBACK_MAX_TOKENS or 1000,
            "temperature": 0.2,
        },
    }
    try:
        import httpx

        with httpx.Client(timeout=30) as client:
            resp = client.post(api_url, json=body)
            if resp.status_code != 200:
                _logger.warning(
                    "general_knowledge_llm http_error status=%s model=%s",
                    resp.status_code,
                    model,
                )
                return None
            data = resp.json()
            answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        _logger.exception("general_knowledge_llm failed model=%s", model)
        return None

    return labeled_non_research_payload(
        answer=answer,
        strategy=strategy if strategy.startswith("llm_fallback") else f"llm_fallback_{model}",
        candidate_count=candidate_count,
        knowledge_kind="general_knowledge",
        banner=GENERAL_KNOWLEDGE_BANNER,
    )
