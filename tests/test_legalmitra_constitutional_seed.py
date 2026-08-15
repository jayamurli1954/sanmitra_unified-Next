"""Validate Tier-1 constitutional doctrine/judgment seed JSON."""
from __future__ import annotations

from app.modules.legal_compat.constitutional_seed import (
    iter_doctrine_records,
    iter_ingest_requests,
    iter_judgment_records,
    load_doctrine_to_cases,
    validate_seed_package,
)


def test_constitutional_seed_package_is_ingest_ready():
    assert validate_seed_package() == []


def test_tier1_counts_and_source_types():
    doctrines = list(iter_doctrine_records())
    judgments = list(iter_judgment_records())
    assert {item["id"] for item in doctrines} == {
        "doctrine_basic_structure",
        "doctrine_stare_decisis",
        "doctrine_ultra_vires",
        "doctrine_severability",
        "doctrine_eclipse",
    }
    assert {item["id"] for item in judgments} == {
        "judgment_kesavananda_bharati_1973",
        "judgment_minerva_mills_1980",
        "judgment_maneka_gandhi_1978",
        "judgment_sr_bommai_1994",
    }
    assert all(item["source_type"] == "doctrine" for item in doctrines)
    assert all(item["source_type"] == "judgment" for item in judgments)
    assert all(item["jurisdiction"] == "India" for item in doctrines + judgments)


def test_ingest_payloads_are_advisory_and_cited():
    payloads = list(iter_ingest_requests())
    assert len(payloads) == 9
    for payload in payloads:
        assert payload.language == "en"
        assert payload.legal_metadata is not None
        assert payload.legal_metadata.jurisdiction == "India"
        assert payload.legal_metadata.act_name == "Constitution of India"
        assert payload.legal_metadata.citation
        assert payload.external_id
        assert payload.metadata["advisory"] is True
        assert payload.metadata["human_review_required"] is True
        assert "human review is required" in payload.content.lower()
        assert "not the full judgment" in payload.content.lower()
        assert payload.source_type in {"doctrine", "judgment"}


def test_judgment_payloads_keep_source_uri_and_citation():
    by_id = {payload.external_id: payload for payload in iter_ingest_requests()}
    kesavananda = by_id["judgment_kesavananda_bharati_1973"]
    assert kesavananda.source_type == "judgment"
    assert kesavananda.legal_metadata.citation == "(1973) 4 SCC 225"
    assert kesavananda.legal_metadata.court_name == "Supreme Court of India"
    assert kesavananda.source_uri and kesavananda.source_uri.startswith("https://indiankanoon.org/")


def test_doctrine_crosswalk_only_references_known_ids():
    mappings = load_doctrine_to_cases()["mappings"]
    doctrine_ids = {item["id"] for item in iter_doctrine_records()}
    judgment_ids = {item["id"] for item in iter_judgment_records()}
    assert set(mappings) <= doctrine_ids
    for case_ids in mappings.values():
        assert set(case_ids) <= judgment_ids
