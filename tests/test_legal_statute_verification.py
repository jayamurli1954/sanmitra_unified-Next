import pytest

from app.modules.legal_compat import service


def _make_rag_result(answer: str = "", citations: list | None = None) -> dict:
    return {"answer": answer, "citations": citations or [], "strategy": "hybrid_hash"}


def test_prompt_includes_canonical_bnss_crosswalk() -> None:
    prompt = service._build_senior_counsel_prompt(
        query="Can an FIR under Section 420 BNS be quashed if the dispute is purely contractual?",
        format_mode="cheat_sheet",
        rag_context="",
        today_ist="2026-05-16",
    )

    assert "CrPC Section 482" in prompt
    assert "BNSS Section 528" in prompt
    assert "Do NOT map CrPC Section 482 to BNSS Section 504, 538" in prompt


def test_ni_act_query_uses_procedure_guide_format() -> None:
    format_mode = service._detect_format_mode(
        "Section 138 NI Act territorial jurisdiction and cheque dishonour complaint procedure",
        "research",
    )
    prompt = service._build_senior_counsel_prompt(
        query="Section 138 NI Act territorial jurisdiction and cheque dishonour complaint procedure",
        format_mode=format_mode,
        rag_context="",
        today_ist="2026-05-16",
    )

    assert format_mode == "procedure_guide"
    assert "PRACTICAL LEGAL PROCEDURE GUIDE" in prompt
    assert "NI Act Sections 142(2) and 142A" in prompt
    assert "Step-by-Step Procedure" in prompt


@pytest.mark.parametrize(
    "query",
    [
        "How to file a consumer complaint for defective goods?",
        "Prepare a GST notice reply procedure and document checklist",
        "What is the filing process for a company law oppression petition?",
        "Give me a step-by-step guide for labour compliance notice reply",
    ],
)
def test_global_procedure_queries_use_procedure_guide_format(query: str) -> None:
    format_mode = service._detect_format_mode(query, "research")

    assert format_mode == "procedure_guide"


@pytest.mark.parametrize(
    ("query_type", "expected"),
    [
        ("explain", "legal_advisor"),
        ("advocate_research", "procedure_guide"),
        ("drafting", "drafting"),
        ("court_strategy", "court_strategy"),
        ("compliance", "compliance"),
    ],
)
def test_legalmitra_output_modes_route_to_expected_formats(query_type: str, expected: str) -> None:
    query = "Section 138 NI Act territorial jurisdiction and cheque dishonour complaint procedure"

    assert service._detect_format_mode(query, query_type) == expected


def test_court_strategy_prompt_includes_advanced_sections() -> None:
    prompt = service._build_senior_counsel_prompt(
        query="Whether a security cheque attracts liability under Section 138 NI Act?",
        format_mode="court_strategy",
        rag_context="",
        today_ist="2026-05-16",
    )

    assert "COURT STRATEGY MODE" in prompt
    assert "Counter-Arguments" in prompt
    assert "Rebuttal Strategy" in prompt
    assert "Drafting Watchpoints" in prompt


def test_procedure_guide_prompt_includes_advanced_litigation_notes() -> None:
    prompt = service._build_senior_counsel_prompt(
        query="Whether a security cheque attracts liability under Section 138 NI Act?",
        format_mode="procedure_guide",
        rag_context="",
        today_ist="2026-05-16",
    )

    assert "Advanced Litigation Notes" in prompt
    assert "Sections 143 and 145" in prompt
    assert "security cheque" in prompt


def test_statute_verifier_corrects_wrong_bnss_482_mappings() -> None:
    response = (
        "Section 482 CrPC is now Section 504 BNSS for inherent powers. "
        "BNSS Section 538 also permits FIR quashing."
    )

    corrected = service.normalize_verified_statute_mappings(
        response,
        query="FIR quashing under Section 482 CrPC",
    )

    assert "Section 504 BNSS" not in corrected
    assert "BNSS Section 538" not in corrected
    assert corrected.count("Section 528 BNSS") >= 2
    assert "Statute Verification" in corrected


@pytest.mark.asyncio
async def test_hybrid_normalizes_gemini_bnss_inherent_power_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_claude(*, prompt: str, max_tokens: int, temperature: float = 0.2) -> str | None:
        return None

    async def _mock_gemini(*, prompt: str, max_tokens: int, temperature: float = 0.2) -> str | None:
        return "CrPC Section 482 is now Section 504 BNSS for quashing FIRs."

    monkeypatch.setattr(service, "_call_claude_legal_counsel_text", _mock_claude)
    monkeypatch.setattr(service, "_call_gemini_text", _mock_gemini)

    result = await service.build_hybrid_legal_response(
        tenant_id="tenant-1",
        app_key="legalmitra",
        query="Can an FIR under Section 420 BNS be quashed if the dispute is purely contractual?",
        rag_result=_make_rag_result(),
        background_tasks=None,
    )

    assert "Section 504 BNSS" not in result["response"]
    assert "Section 528 BNSS" in result["response"]
    assert "Statute Verification" in result["response"]
