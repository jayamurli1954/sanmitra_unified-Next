"""Tests for curated IPC/CrPC <-> BNS/BNSS crosswalk tool."""
from __future__ import annotations

from app.modules.legal_compat import code_crosswalk as cx
from app.modules.legal_compat.statute_normalize import normalize_verified_statute_mappings


def test_lookup_ipc_420_to_bns_318():
    result = cx.lookup(from_code="IPC", section="420")
    assert result["found"] is True
    assert result["matches"][0]["to_code"] == "BNS"
    assert str(result["matches"][0]["to_section"]).startswith("318")
    assert result["human_review_required"] is True


def test_lookup_ipc_34_to_bns_3_5():
    result = cx.lookup(from_code="IPC", section="34")
    assert result["found"] is True
    assert result["matches"][0]["to_section"] == "3(5)"


def test_sections_compatible_parent_subsection():
    assert cx.sections_compatible("318", "318(4)")
    assert cx.sections_compatible("318(4)", "318")
    assert not cx.sections_compatible("318", "319")


def test_lookup_crpc_458_to_bnss_504_seized_property():
    result = cx.lookup(from_code="CrPC", section="458")
    assert result["found"] is True
    assert result["matches"][0]["to_code"] == "BNSS"
    assert result["matches"][0]["to_section"] == "504"


def test_lookup_crpc_482_to_bnss_528():
    result = cx.lookup(from_code="CrPC", section="482")
    assert result["found"] is True
    assert result["matches"][0]["to_section"] == "528"


def test_lookup_crpc_154_to_bnss_173():
    result = cx.lookup(from_code="CrPC", section="154")
    assert result["found"] is True
    assert result["matches"][0]["to_section"] == "173"


def test_lookup_crpc_41a_to_bnss_35_3():
    result = cx.lookup(from_code="CrPC", section="41A")
    assert result["found"] is True
    assert result["matches"][0]["to_section"] == "35(3)"


def test_reverse_lookup_bnss_528():
    result = cx.lookup(from_code="BNSS", section="528", direction="reverse")
    assert result["found"] is True
    assert result["matches"][0]["from_code"] == "CrPC"
    assert result["matches"][0]["from_section"] == "482"


def test_missing_mapping_does_not_invent():
    result = cx.lookup(from_code="IPC", section="9999")
    assert result["found"] is False
    assert result["matches"] == []
    assert "Do not invent" in (result.get("not_found_policy") or "")


def test_detect_false_crpc_482_to_bnss_504():
    false = cx.detect_false_mapping(
        from_code="CrPC",
        from_section="482",
        to_code="BNSS",
        to_section="504",
    )
    assert false is not None
    assert false["correct_to_section"] == "528"


def test_detect_false_ipc_504_to_bnss_504():
    false = cx.detect_false_mapping(
        from_code="IPC",
        from_section="504",
        to_code="BNSS",
        to_section="504",
    )
    assert false is not None
    assert false["correct_to_code"] == "BNS"
    assert false["correct_to_section"] == "352"


def test_normalizer_preserves_genuine_bnss_504_outside_482_context():
    text = (
        "Under BNSS Section 504, where no claimant appears within six months "
        "for seized property, the Magistrate may place it at the disposal of the State."
    )
    out = normalize_verified_statute_mappings(text, query="procedure for unclaimed seized property")
    assert "Section 504" in out or "BNSS Section 504" in out
    assert "Section 528 BNSS" not in out


def test_normalizer_rewrites_482_false_map_to_528():
    text = "For FIR quashing, invoke Section 504 BNSS as the successor to CrPC 482."
    out = normalize_verified_statute_mappings(text, query="quash FIR under inherent powers CrPC 482")
    assert "Section 528 BNSS" in out
    assert "Statute Verification" in out


def test_normalizer_rewrites_ipc_504_false_bnss_map():
    text = "IPC Section 504 is now BNSS Section 504 for intentional insult."
    out = normalize_verified_statute_mappings(text, query="IPC 504 intentional insult")
    assert "BNS Section 352" in out
    assert "intentional insult" in out.lower()


def test_lookup_iea_65b_to_bsa_63():
    result = cx.lookup(from_code="IEA", section="65B")
    assert result["found"] is True
    assert result["matches"][0]["to_code"] == "BSA"
    assert result["matches"][0]["to_section"] == "63"


def test_lookup_iea_25_to_bsa_23():
    result = cx.lookup(from_code="IEA", section="25")
    assert result["found"] is True
    assert str(result["matches"][0]["to_section"]).startswith("23")


def test_prompt_snippet_includes_high_risk_pairs():
    snippet = cx.prompt_crosswalk_snippet(max_rows=5)
    assert "CrPC 482" in snippet
    assert "BNSS 528" in snippet
    assert "do not invent" in snippet.lower()
