"""Unit tests for LegalMitra curated judgment retrieve-or-refuse."""
from __future__ import annotations

from app.modules.legal_compat.judgment_retrieval import (
    format_judgments_block,
    query_wants_judgments,
    retrieve_judgments,
)


def test_query_wants_judgments_detects_referred_cases():
    assert query_wants_judgments("GST Section 54 with some referred cases") is True
    assert query_wants_judgments("What is the time limit under Section 54?") is False


def test_retrieve_vkc_for_section_54_refund_case_query():
    hits = retrieve_judgments(
        "CGST Section 54 GST refund time limit and referred cases / judgments",
        corpus_key="cgst_section_54",
    )
    assert hits
    assert "vkc" in str(hits[0].get("title") or "").lower()
    focus = str(hits[0].get("topic_focus") or "").lower()
    assert "not a section 54(1) limitation" in focus


def test_format_refuse_when_no_hits():
    block = format_judgments_block([], wants_cases=True)
    assert "no matching judgments retrieved" in block.lower()
    assert "will not invent" in block.lower()


def test_format_not_searched_when_cases_not_requested():
    block = format_judgments_block([], wants_cases=False)
    assert "not searched" in block.lower()
