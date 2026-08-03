"""Query-aware insufficient-sources next steps must match the tool topic."""
from __future__ import annotations

import pytest

from app.modules.legal_compat.response_contract import (
    _insufficient_sources_next_steps,
    insufficient_sources_response,
)

# Mirrors the six homepage Legal Tools "Open in LegalMitra AI" default queries.
TOOL_QUERIES = {
    "court-fee": "Calculate court fee for a civil suit in India and explain state-wise caveats",
    "gst-finder": "Find GST rate and HSN or SAC code checklist for an Indian business transaction",
    "notice-drafter": "Draft a legal notice checklist for money recovery under Indian law",
    "limitation": "Calculate limitation period and filing deadline checklist under Indian law",
    "stamp-duty": "Explain stamp duty and registration charge checklist for an Indian property transaction",
    "hsn-search": "Find HSN code search checklist and GST invoice classification risks",
}


@pytest.mark.parametrize("tool_key,question", list(TOOL_QUERIES.items()))
def test_tool_queries_do_not_all_get_gst_refund_section_54(tool_key: str, question: str) -> None:
    steps = _insufficient_sources_next_steps(question)
    joined = "\n".join(steps).lower()
    body = str(insufficient_sources_response(question=question).get("response") or "").lower()

    if tool_key in {"gst-finder", "hsn-search"}:
        assert "section 54" not in joined
        assert "refund" not in joined or "rate" in joined or "hsn" in joined
        assert "hsn" in joined or "rate" in joined or "classification" in joined
    else:
        assert "cgst act section 54" not in joined
        assert "cgst act section 54" not in body
        assert "for gst refunds" not in joined


def test_limitation_query_suggests_limitation_not_gst_refund() -> None:
    question = TOOL_QUERIES["limitation"]
    steps = _insufficient_sources_next_steps(question)
    joined = "\n".join(steps).lower()
    assert "limitation" in joined or "cause of action" in joined
    assert "section 54" not in joined


def test_gst_refund_query_still_suggests_section_54_family() -> None:
    question = "What is the time limit to claim GST refund under CGST Act Section 54?"
    steps = _insufficient_sources_next_steps(question)
    joined = "\n".join(steps).lower()
    assert "section 54" in joined


def test_generic_query_uses_neutral_narrowing_tip() -> None:
    steps = _insufficient_sources_next_steps("Explain vakalatnama drafting etiquette")
    joined = "\n".join(steps).lower()
    assert "cgst" not in joined
    assert "narrow the query" in joined
