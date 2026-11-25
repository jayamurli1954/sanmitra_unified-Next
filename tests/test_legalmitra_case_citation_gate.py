"""Case-citation gate: case authorities must be traceable to retrieved sources."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.legal_compat import service
from app.modules.legal_compat.case_citation_audit import (
    REDACTION_MARKER,
    audit_case_citations,
    find_case_claims,
    redact_unsupported_case_citations,
)
from app.modules.legal_compat.quality_gate import (
    CASE_REDACTION_LIMITATION,
    apply_research_trust_layers,
    run_quality_gate,
)
from app.modules.legal_compat.response_contract import finalize_research_response

FIXTURE = Path(__file__).parent / "fixtures" / "legalmitra_case_citation_fault_eval.json"

VKC_CITATION = {
    "title": "Union of India v. VKC Footsteps (India) Pvt Ltd",
    "snippet": "Inverted duty structure refund under Section 54(3).",
    "legal_metadata": {"citation": "2021 SCC OnLine SC 706"},
}


# ── Detection ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Kesavananda Bharati v. State of Kerala held so.", "Kesavananda Bharati v. State of Kerala"),
        ("In Union of India v. VKC Footsteps (India) (P) Ltd., the Court", "Union of India v. VKC Footsteps (India) (P) Ltd."),
        ("See *Mohit Minerals Pvt. Ltd. vs. Union of India*.", "Mohit Minerals Pvt. Ltd. vs. Union of India"),
        ("State of U.P. Vs Raj Narain is cited.", "State of U.P. Vs Raj Narain"),
        ("Part V of the Constitution. State of Haryana v. Bhajan Lal applies.", "State of Haryana v. Bhajan Lal"),
    ],
)
def test_find_case_names(text: str, expected: str) -> None:
    names = [c["text"] for c in find_case_claims(text) if c["claim_type"] == "case_name"]
    assert names == [expected]


@pytest.mark.parametrize(
    "citation",
    [
        "(1973) 4 SCC 225",
        "AIR 1973 SC 1461",
        "2021 SCC OnLine SC 706",
        "1992 Supp (1) SCC 335",
        "(2017) 52 GSTL 513 (SC)",
        "[2021] 3 SCR 1",
        "(2019) 418 ITR 1",
    ],
)
def test_find_reporter_citations(citation: str) -> None:
    claims = find_case_claims(f"As reported in {citation}, the rule applies.")
    assert [c["text"] for c in claims if c["claim_type"] == "reporter_citation"] == [citation]


@pytest.mark.parametrize(
    "text",
    [
        "Section 54 of the CGST Act governs refunds within two years.",
        "Part V of the Constitution deals with the Union.",
        "Rule 89(5) prescribes the formula; see Section 54(3).",
        "BNS 2023 replaces IPC 1860 and BNSS replaces CrPC 1973.",
    ],
)
def test_no_false_positives_on_statute_text(text: str) -> None:
    assert find_case_claims(text) == []


# ── Audit / redaction ───────────────────────────────────────────────────────


def test_supported_case_and_citation_are_kept() -> None:
    text = "In Union of India v. VKC Footsteps (India) (P) Ltd., 2021 SCC OnLine SC 706, Rule 89(5) was upheld."
    redacted, audit = redact_unsupported_case_citations(response_text=text, citations=[VKC_CITATION])
    assert redacted == text
    assert audit["unsupported_count"] == 0
    assert audit["verified_count"] == 2


def test_unsupported_case_with_citation_is_removed_as_one_unit() -> None:
    text = "**Key SC Case:** Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225 — basic structure."
    redacted, audit = redact_unsupported_case_citations(response_text=text, citations=[VKC_CITATION])
    assert "Kesavananda" not in redacted
    assert "SCC 225" not in redacted
    assert redacted.count(REDACTION_MARKER) == 1
    assert redacted.startswith("**Key SC Case:** ")
    assert redacted.endswith("— basic structure.")
    assert audit["unsupported_count"] == 2


def test_generic_party_overlap_is_not_enough() -> None:
    # Only "Union of India" overlaps; the distinctive party is absent.
    audit = audit_case_citations(
        response_text="Mohit Minerals Pvt. Ltd. v. Union of India decided this.",
        citations=[VKC_CITATION],
    )
    assert audit["unsupported_count"] == 1


def test_citation_from_other_case_does_not_launder_fabricated_name() -> None:
    text = "Fake Traders v. Union of India, 2021 SCC OnLine SC 706."
    redacted, _ = redact_unsupported_case_citations(response_text=text, citations=[VKC_CITATION])
    assert "Fake Traders" not in redacted
    assert "706" not in redacted


def test_no_evidence_means_every_case_is_unsupported() -> None:
    audit = audit_case_citations(
        response_text="Kesavananda Bharati v. State of Kerala.", citations=[]
    )
    assert audit["unsupported_count"] == 1


# ── Trust layer integration ─────────────────────────────────────────────────


def _payload(response: str, citations: list[dict], strategy: str = "rag_claude_legal_counsel") -> dict:
    return finalize_research_response(
        question="GST refund in India",
        response=response,
        citations=citations,
        strategy=strategy,
        jurisdiction="India (Central)",
        confidence="high",
    )


def test_trust_layer_redacts_and_records_case_audit() -> None:
    out = apply_research_trust_layers(
        _payload(
            "Section 54 applies. Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225.",
            [{"title": "CGST Act Section 54", "snippet": "Section 54 refund"}],
        )
    )
    assert "Kesavananda" not in out["response"]
    assert out["case_citation_audit"]["unsupported_count"] == 2
    assert out["case_citation_audit"]["remaining_unsupported_count"] == 0
    assert CASE_REDACTION_LIMITATION in out["limitations"]
    assert out["confidence"] == "medium"
    assert out["quality_gate"]["passed"] is True
    check = next(c for c in out["quality_gate"]["checks"] if c["id"] == "QG-CASE-CITATIONS")
    assert check["status"] == "pass"


def test_trust_layer_leaves_clean_answer_untouched() -> None:
    payload = _payload(
        "Section 54 applies; see Union of India v. VKC Footsteps (India) Pvt Ltd [R1].",
        [VKC_CITATION, {"title": "CGST Act Section 54", "snippet": "Section 54 refund"}],
    )
    out = apply_research_trust_layers(payload)
    assert out["response"] == payload["response"]
    assert CASE_REDACTION_LIMITATION not in out["limitations"]
    assert out["case_citation_audit"]["unsupported_count"] == 0


def test_curated_offline_strategy_is_not_redacted() -> None:
    text = "Section 54. Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225."
    out = apply_research_trust_layers(
        _payload(text, [{"title": "CGST s.54", "snippet": "Section 54"}], strategy="offline_test_package")
    )
    assert "Kesavananda" in out["response"]
    assert "case_citation_audit" not in out


def test_quality_gate_fails_if_unsupported_case_remains() -> None:
    payload = _payload("x", [{"title": "t"}])
    payload["case_citation_audit"] = {"unsupported_count": 1, "remaining_unsupported_count": 1}
    gate = run_quality_gate(payload)
    assert "QG-CASE-CITATIONS" in gate["failed_ids"]


# ── Fault-fixture eval through the full hybrid path ─────────────────────────


def _fault_cases() -> list[dict]:
    return list(json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"])


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _fault_cases(), ids=lambda c: c["id"])
async def test_case_citation_fault_fixture(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _inject(**_kwargs):
        return case["inject_provider_text"]

    async def _no_gemini(**_kwargs):
        return None

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _inject)
    monkeypatch.setattr(service, "_call_gemini_text", _no_gemini)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query=case["question"],
        rag_result={"answer": "", "strategy": "hybrid_hash", "citations": case["citations"]},
        background_tasks=None,
    )
    expect = case["expect"]
    body = str(result.get("response") or "").lower()

    assert result["strategy"].endswith("claude_legal_counsel"), result["strategy"]
    assert result["quality_gate"]["passed"] is True, result["quality_gate"]
    assert result["human_review_required"] is True
    for term in expect.get("must_include_terms") or []:
        assert term.lower() in body, term
    for term in expect.get("forbid_terms") or []:
        assert term.lower() not in body, term
    audit = result["case_citation_audit"]
    assert audit["remaining_unsupported_count"] == 0
    if "min_unsupported" in expect:
        assert audit["unsupported_count"] >= expect["min_unsupported"]
    if "max_unsupported" in expect:
        assert audit["unsupported_count"] <= expect["max_unsupported"]
