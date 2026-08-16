"""Stage 2.1 Quality Gate + statute-first Citation Audit tests."""
from __future__ import annotations

import pytest

from app.modules.legal_compat import service
from app.modules.legal_compat.citation_audit import (
    audit_statute_section_claims,
    extract_section_numbers,
)
from app.modules.legal_compat.quality_gate import enforce_quality_gate, run_quality_gate
from app.modules.legal_compat.response_contract import finalize_research_response


def test_extract_section_numbers_unique_order() -> None:
    text = "Under Section 54 and Sec. 54A, see also s. 139 of the Act. Section 54 again."
    assert extract_section_numbers(text) == ["54", "54A", "139"]


def test_citation_audit_verifies_supported_section() -> None:
    audit = audit_statute_section_claims(
        response_text="CGST Act Section 54 sets the refund time limit.",
        citations=[{"title": "CGST Act s.54", "snippet": "Section 54 — refund of tax"}],
    )
    assert audit["mismatch_count"] == 0
    assert audit["verified_count"] == 1
    assert audit["claims"][0]["outcome"] == "verified"


def test_citation_audit_flags_unsupported_section() -> None:
    audit = audit_statute_section_claims(
        response_text="You must file under Section 999 of the CGST Act.",
        citations=[{"title": "CGST Act s.54", "snippet": "Section 54 — refund of tax"}],
    )
    assert audit["mismatch_count"] == 1
    assert audit["claims"][0]["section"] == "999"
    assert audit["claims"][0]["outcome"] == "mismatch"


def test_quality_gate_repairs_human_review_and_advisory() -> None:
    payload = finalize_research_response(
        question="GST refund under Section 54?",
        response="Section 54 governs refunds.",
        citations=[{"title": "CGST Act s.54", "snippet": "Section 54 refund"}],
        strategy="test",
        jurisdiction="India (Central)",
    )
    payload["human_review_required"] = False
    payload["advisory_notice"] = ""
    audit = audit_statute_section_claims(
        response_text=payload["response"],
        citations=payload["citations"],
    )
    out = enforce_quality_gate(payload, citation_audit=audit)
    assert out["human_review_required"] is True
    assert out["advisory_notice"]
    assert out["quality_gate"]["passed"] is True


def test_quality_gate_fails_when_citations_missing_on_grounded_answer() -> None:
    payload = {
        "question": "What is Section 54?",
        "jurisdiction": "India (Central)",
        "missing_jurisdiction": False,
        "confidence": "medium",
        "citations": [],
        "limitations": ["x"],
        "human_review_required": True,
        "advisory_notice": "advisory",
        "strategy": "rag_gemini",
        "generated_at": "2026-08-01T00:00:00+00:00",
    }
    gate = run_quality_gate(payload, citation_audit=None, skip_citation_presence=False)
    assert gate["passed"] is False
    assert "QG-CITATIONS" in gate["failed_ids"]


@pytest.mark.asyncio
async def test_hybrid_refuses_fabricated_section_not_in_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_claude(**_kwargs):
        return None

    async def _mock_gemini(**_kwargs):
        return (
            "File the claim under Section 999 of the CGST Act for an automatic refund."
        )

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_claude)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_gemini)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="What is the GST refund time limit under CGST Section 54?",
        rag_result={
            "answer": "",
            "strategy": "hybrid_hash",
            "citations": [
                {
                    "title": "CGST Act Section 54",
                    "snippet": "Section 54 provides for refund of tax.",
                    "score": 0.9,
                }
            ],
        },
        background_tasks=None,
    )

    # Hallucinated Section 999 must not ship. With RAG citations already present,
    # do not paper over the audit refusal with a canned offline package — that
    # hid corpus utilization when providers failed or fabricated under
    # LEGAL_RAG_ENABLED=true. Prefer the Stage 2.1 insufficient_sources refusal.
    assert result["strategy"] == "insufficient_sources"
    assert result["confidence"] == "insufficient_sources"
    assert result["human_review_required"] is True
    body = str(result.get("response") or "").lower()
    assert "section 999" not in body
    assert "automatic refund" not in body
    assert "file the claim under section 999" not in body


@pytest.mark.asyncio
async def test_offline_section_54_case_request_retrieves_corpus_judgments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_provider(**_kwargs):
        raise AssertionError("Provider must not run for authorized GST offline slice")

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_provider)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_provider)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="CGST Section 54 GST refund time limit and referred cases / judgments",
        rag_result={"answer": "", "strategy": "hybrid_hash", "citations": []},
        background_tasks=None,
    )

    assert result["strategy"] == "offline_cgst_section_54_refund_fallback"
    body = str(result.get("response") or "").lower()
    assert "vkc footsteps" in body
    assert "corpus-backed" in body
    assert "will not invent" not in body  # hit path — refuse text not used
    assert any(
        (c.get("source_type") == "judgment")
        and "vkc" in str(c.get("title") or "").lower()
        for c in (result.get("citations") or [])
    )
    assert result["citation_audit"]["mismatch_count"] == 0
    assert result["quality_gate"]["passed"] is True


@pytest.mark.asyncio
async def test_offline_section_54_case_request_refuses_when_corpus_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_provider(**_kwargs):
        raise AssertionError("Provider must not run for authorized GST offline slice")

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_provider)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_provider)
    monkeypatch.setattr(
        "app.modules.legal_compat.offline_fallbacks.retrieve_judgments",
        lambda *_a, **_k: [],
    )

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="CGST Section 54 GST refund referred cases",
        rag_result={"answer": "", "strategy": "hybrid_hash", "citations": []},
        background_tasks=None,
    )
    body = str(result.get("response") or "").lower()
    assert "no matching judgments retrieved" in body
    assert "will not invent" in body
    assert result["citation_audit"]["mismatch_count"] == 0
    assert result["quality_gate"]["passed"] is True


@pytest.mark.asyncio
async def test_hybrid_audit_mismatch_without_offline_slice_still_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no authorized offline slice matches, audit refusal must remain."""

    async def _mock_claude(**_kwargs):
        return None

    async def _mock_gemini(**_kwargs):
        return "Apply Section 777 of the mythical Compliance Act immediately."

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_claude)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_gemini)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="Explain vakalatnama drafting etiquette for chamber practice in India",
        rag_result={
            "answer": "",
            "strategy": "hybrid_hash",
            "citations": [
                {
                    "title": "Advocate chamber practice note",
                    "snippet": "Vakalatnama etiquette and client communication norms.",
                    "score": 0.9,
                }
            ],
        },
        background_tasks=None,
    )

    assert result["strategy"] == "insufficient_sources"
    assert result["confidence"] == "insufficient_sources"
    assert int((result.get("citation_audit") or {}).get("mismatch_count") or 0) >= 1


@pytest.mark.asyncio
async def test_hybrid_gst_offline_still_passes_stage21_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(**_kwargs):
        raise AssertionError("provider must not run")

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _boom)
    monkeypatch.setattr(service, "_call_gemini_text", _boom)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="What is the time limit to claim GST refund under CGST Act Section 54?",
        rag_result={"answer": "", "citations": [], "strategy": "hybrid_hash"},
        background_tasks=None,
    )

    assert result["confidence"] != "insufficient_sources"
    assert result["quality_gate"]["passed"] is True
    assert result.get("citation_audit") is not None
    assert result["citation_audit"]["mismatch_count"] == 0
