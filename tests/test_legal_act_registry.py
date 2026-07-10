from app.modules.rag.legal_act_registry import (
    detect_legal_act,
    legal_act_metadata_filter,
    should_trigger_jit,
)


def test_detects_bnss_without_confusing_it_for_bns() -> None:
    match = detect_legal_act("Explain FIR registration procedure under section 173 BNSS")

    assert match is not None
    assert match.key == "bnss"
    assert "Nagarik Suraksha" in match.canonical_name


def test_detects_bns_when_bns_is_actually_asked() -> None:
    match = detect_legal_act("What is the punishment under section 103 BNS?")

    assert match is not None
    assert match.key == "bns"
    assert "Nyaya Sanhita" in match.canonical_name


def test_detects_ni_act_as_negotiable_instruments_act() -> None:
    match = detect_legal_act("Whether a security cheque attracts liability under NI Act?")

    assert match is not None
    assert match.key == "negotiable_instruments"
    assert match.canonical_name == "Negotiable Instruments Act, 1881"


def test_metadata_filter_includes_canonical_and_aliases() -> None:
    match = detect_legal_act("section 138 cheque dishonour limitation")

    assert match is not None
    metadata_filter = legal_act_metadata_filter(match)

    assert metadata_filter["$options"] == "i"
    assert "Negotiable\\ Instruments\\ Act" in metadata_filter["$regex"]
    assert "cheque\\ dishonour" in metadata_filter["$regex"]


def test_should_trigger_jit_for_generic_statute_queries() -> None:
    assert should_trigger_jit("Find the bare act text for limitation rules")
    assert should_trigger_jit("Explain section 107 GST appeal limitation")
