"""Phase 0: uncited LLM fallback stays labeled and off by default."""
from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.modules.rag.fallback import (
    GENERAL_KNOWLEDGE_BANNER,
    INSUFFICIENT_INDEX_ANSWER,
    insufficient_index_payload,
    labeled_non_research_payload,
    try_general_knowledge_llm,
)
from app.modules.rag.schemas import RagQueryResponse

ROOT = Path(__file__).resolve().parents[1]


def test_repo_defaults_disable_uncited_llm_fallback():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "LEGAL_HYBRID_AI_FALLBACK_ENABLED=false" in example
    assert 'LEGAL_HYBRID_AI_FALLBACK_ENABLED' in render
    assert 'value: "false"' in render.split("LEGAL_HYBRID_AI_FALLBACK_ENABLED", 1)[1][:80]


def test_try_general_knowledge_llm_returns_none_when_flag_off(monkeypatch):
    monkeypatch.setattr(Settings, "LEGAL_HYBRID_AI_FALLBACK_ENABLED", False)
    monkeypatch.setattr(Settings, "GEMINI_API_KEY", "dummy-key")
    assert try_general_knowledge_llm(query="What is Article 141?", strategy="llm_fallback", candidate_count=0) is None


def test_labeled_general_knowledge_payload_is_not_research():
    payload = labeled_non_research_payload(
        answer="Parliament cannot destroy the basic structure.",
        strategy="llm_fallback_empty_db",
        candidate_count=0,
        knowledge_kind="general_knowledge",
        banner=GENERAL_KNOWLEDGE_BANNER,
    )
    assert payload["citations"] == []
    assert payload["is_source_backed_research"] is False
    assert payload["is_fallback"] is True
    assert payload["knowledge_kind"] == "general_knowledge"
    assert payload["human_review_required"] is True
    assert "GENERAL KNOWLEDGE ONLY" in payload["answer"]
    assert "not source-backed legal research" in payload["answer"].lower()
    parsed = RagQueryResponse(**{k: v for k, v in payload.items() if k in RagQueryResponse.model_fields})
    assert parsed.is_source_backed_research is False
    assert parsed.knowledge_kind == "general_knowledge"


def test_insufficient_index_payload_refuses_uncited_answer():
    payload = insufficient_index_payload(
        strategy="hash-v2",
        candidate_count=0,
        include_context=False,
        reason="empty_index",
    )
    assert payload["citations"] == []
    assert payload["knowledge_kind"] == "insufficient_sources"
    assert payload["is_fallback"] is False
    assert "will not invent" in payload["answer"].lower()
    assert INSUFFICIENT_INDEX_ANSWER in payload["answer"]
