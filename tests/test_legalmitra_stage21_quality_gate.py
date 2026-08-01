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

    assert result["strategy"] == "insufficient_sources"
    assert result["confidence"] == "insufficient_sources"
    assert result["citation_audit"]["mismatch_count"] >= 1
    assert result["quality_gate"]["passed"] is True
    assert result["human_review_required"] is True


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
