"""Stage 2 LegalMitra RAG response contract and GST Section 54 slice tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.legal_compat import service
from app.modules.legal_compat.response_contract import (
    finalize_research_response,
    resolve_jurisdiction,
)


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "legalmitra_gst_s54_eval.json"


def _make_rag_result(citations: list | None = None) -> dict:
    return {"answer": "", "citations": citations or [], "strategy": "hybrid_hash"}


def test_finalize_research_response_always_requires_human_review() -> None:
    payload = finalize_research_response(
        question="What is CGST Section 54?",
        response="Section 54 governs GST refunds.",
        citations=[{"title": "CGST Act s.54", "snippet": "refund of tax"}],
        strategy="test",
        jurisdiction="India (Central)",
    )
    assert payload["human_review_required"] is True
    assert payload["confidence"] in {"high", "medium", "low"}
    assert payload["advisory_notice"]
    assert payload["generated_at"]
    assert payload["citations"][0]["retrieved_at"]
    assert payload["citations"][0]["staleness_status"]
    assert payload["knowledge_kind"] == "source_backed_research"
    assert payload["is_source_backed_research"] is True


def test_resolve_jurisdiction_infers_india_central_for_gst() -> None:
    jurisdiction, missing = resolve_jurisdiction("GST refund under Section 54 CGST Act")
    assert jurisdiction == "India (Central)"
    assert missing is False


def test_resolve_jurisdiction_blocks_state_gst_without_state() -> None:
    jurisdiction, missing = resolve_jurisdiction(
        "What is the state GST refund special rate notification under SGST?"
    )
    assert jurisdiction is None
    assert missing is True


@pytest.mark.asyncio
async def test_hybrid_refuses_when_no_relevant_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"gemini": False, "claude": False}

    async def _mock_claude(**kwargs):
        called["claude"] = True
        return "Should not be used"

    async def _mock_gemini(**kwargs):
        called["gemini"] = True
        return "Should not be used"

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_claude)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_gemini)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="what is vakalatnama drafting etiquette in obscure village bye-laws",
        rag_result=_make_rag_result([]),
        background_tasks=None,
    )

    assert result["confidence"] == "insufficient_sources"
    assert result["strategy"] == "insufficient_sources"
    assert result["knowledge_kind"] == "insufficient_sources"
    assert result["is_source_backed_research"] is False
    assert result["human_review_required"] is True
    assert called["gemini"] is False
    assert called["claude"] is False
    assert "insufficient" in result["response"].lower()
    assert "cgst act section 54" not in result["response"].lower()
    assert "gst refunds" not in result["response"].lower()


@pytest.mark.asyncio
async def test_hybrid_gst_section_54_offline_slice_is_citation_backed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_provider(**kwargs):
        raise AssertionError("Provider must not run when authorized GST offline slice applies")

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_provider)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_provider)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="What is the time limit to claim GST refund under CGST Act Section 54?",
        rag_result=_make_rag_result([]),
        background_tasks=None,
    )

    assert result["strategy"] == "offline_cgst_section_54_refund_fallback"
    assert result["human_review_required"] is True
    assert result["jurisdiction"] == "India (Central)"
    assert result["confidence"] in {"medium", "high"}
    assert result["citations"]
    body = result["response"].lower()
    assert "section 54" in body
    assert "two years" in body
    assert "relevant date" in body
    assert "direct answer" in body
    assert "authorities retrieved" in body
    assert "practical note" in body
    assert "related provisions" in body
    assert "| refund / claim situation |" in body
    assert "no matching judgments" not in body  # cases not requested
    assert result.get("citation_audit", {}).get("mismatch_count", 0) == 0
    assert result.get("quality_gate", {}).get("passed") is True


@pytest.mark.asyncio
async def test_hybrid_drops_irrelevant_citations_and_refuses_uncited_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_gemini(**kwargs):
        return "Gemini should not answer without sources"

    monkeypatch.setattr(service, "_call_gemini_text", _mock_gemini)
    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_gemini)

    irrelevant = {
        "index": 1,
        "title": "GST rates for composite supply under Indian tax law",
        "snippet": "Goods and Services Tax composite supply bundled services rate notification",
        "reference": "[1] gst source",
    }
    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="liability contractor painting contract act owner materials",
        rag_result=_make_rag_result([irrelevant]),
        background_tasks=None,
    )

    assert result["citations"] == []
    assert result["dropped_citation_count"] == 1
    assert result["confidence"] == "insufficient_sources"
    assert result["strategy"] == "insufficient_sources"


@pytest.mark.asyncio
async def test_hybrid_it_section_139_offline_slice_is_citation_backed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_provider(**kwargs):
        raise AssertionError("Provider must not run when authorized IT offline slice applies")

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_provider)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_provider)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="Who must file a return of income under Income-tax Act Section 139?",
        rag_result=_make_rag_result([]),
        background_tasks=None,
    )

    assert result["strategy"] == "offline_it_section_139_return_fallback"
    assert result["human_review_required"] is True
    assert result["jurisdiction"] == "India (Central)"
    assert result["citations"]
    body = result["response"].lower()
    assert "section 139" in body
    assert "return of income" in body


@pytest.mark.asyncio
async def test_gst_s54_eval_fixture_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_provider(**kwargs):
        return None

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_provider)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_provider)

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for case in fixture["cases"]:
        result = await service.build_hybrid_legal_response(
            tenant_id="tenant-1",
            app_key="legalmitra",
            query=case["question"],
            rag_result=_make_rag_result([]),
            background_tasks=None,
        )
        expect = case["expect"]
        assert result["human_review_required"] is True
        assert result.get("advisory_notice")
        if expect.get("strategy"):
            assert result["strategy"] == expect["strategy"], case["id"]
        if expect.get("confidence"):
            assert result["confidence"] == expect["confidence"], case["id"]
        if expect.get("missing_jurisdiction"):
            assert result["missing_jurisdiction"] is True, case["id"]
        if expect.get("forbid_uncited_generation"):
            assert result["strategy"] != "hybrid_hash_gemini"
            assert result["strategy"] != "hybrid_hash_claude_legal_counsel"
            if result["confidence"] != "insufficient_sources" and not result.get("missing_jurisdiction"):
                assert result["citations"], case["id"]
        for term in expect.get("must_include_terms") or []:
            assert term.lower() in result["response"].lower(), f"{case['id']}: missing {term}"
