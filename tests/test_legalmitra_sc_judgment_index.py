"""Supreme Court open-data judgment index + its use in the Citation Checker."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.main import app
from app.modules.legal_compat import citation_checker as cc
from app.modules.legal_compat import sc_judgment_index as sc


@pytest.fixture(scope="module")
def index() -> sc.SupremeCourtIndex:
    ix = sc.get_index()
    assert len(ix) > 35_000, "run scripts/build_sc_judgment_index.py to build the index"
    return ix


# ── Index lookups (real data) ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("citation", "nc"),
    [
        ("2021 INSC 469", "2021 INSC 469"),
        ("[2021] 15 S.C.R. 169", "2021 INSC 469"),
        ("(2021) 15 SCR 169", "2021 INSC 469"),
        ("[1973] SUPP. 1 S.C.R. 1", "1973 INSC 91"),
    ],
)
def test_by_citation(index, citation: str, nc: str) -> None:
    assert index.by_citation(citation)["nc"] == nc


@pytest.mark.parametrize(
    ("name", "year", "nc"),
    [
        ("Kesavananda Bharati v. State of Kerala", 1973, "1973 INSC 91"),
        ("Golaknath v. State of Punjab", None, "1967 INSC 45"),  # "GOLAK NATH" in source
        ("Maneka Gandhi v. Union of India", None, "1978 INSC 16"),
        ("Arnesh Kumar v. State of Bihar", 2014, "2014 INSC 463"),
        ("Vidya Drolia v. Durga Trading Corporation", 2021, "2020 INSC 697"),  # SCC year = decision year + 1
    ],
)
def test_by_name(index, name: str, year: int | None, nc: str) -> None:
    rows = index.by_name(name, year=year)
    assert [r["nc"] for r in rows] == [nc]


def test_generic_party_must_also_match(index) -> None:
    # "Buffalo Traders ... v. Maneka Gandhi" must not match "Maneka Gandhi v. Union of India".
    titles = [r["t"] for r in index.by_name("Maneka Gandhi v. Union of India")]
    assert all("BUFFALO" not in t for t in titles)


def test_unknown_case_has_no_match(index) -> None:
    assert index.by_name("Ramesh Textiles v. Union of India") == []


def test_pdf_url_points_at_public_bucket(index) -> None:
    url = sc.pdf_url(index.by_citation("2021 INSC 469"))
    assert url == (
        "https://indian-supreme-court-judgments.s3.amazonaws.com/"
        "data/pdf/year=2021/english/2021_15_169_282_EN.pdf"
    )


def test_index_from_rows_without_file() -> None:
    ix = sc.SupremeCourtIndex(
        [{"p": "ABC LTD.", "r": "XYZ MILLS", "nc": "2020 INSC 1", "scr": "[2020] 1 S.C.R. 5", "y": 2020, "path": "p1"}]
    )
    row = ix.by_citation("2020 INSC 1")
    assert row["t"] == "ABC LTD. versus XYZ MILLS"
    assert ix.by_name("ABC Ltd v. XYZ Mills")[0]["nc"] == "2020 INSC 1"


# ── Citation Checker integration ───────────────────────────────────────────


async def _item(text: str) -> dict:
    result = await cc.check_citations(text)
    return next(i for i in result["items"] if i["kind"] == "case")


@pytest.mark.asyncio
async def test_scc_cited_case_found_by_name_and_year() -> None:
    item = await _item("Arnesh Kumar v. State of Bihar, (2014) 8 SCC 273.")
    assert item["status"] == "found_sc"
    assert item["severity"] == "ok"
    assert "page citation itself was not checked" in item["message"]
    assert item["supreme_court_matches"][0]["neutral_citation"] == "2014 INSC 463"
    assert item["supreme_court_matches"][0]["pdf_url"].endswith("_EN.pdf")


@pytest.mark.asyncio
async def test_neutral_citation_verified() -> None:
    item = await _item("Union of India v. VKC Footsteps India Pvt Ltd, 2021 INSC 469.")
    assert item["status"] == "verified"


@pytest.mark.asyncio
async def test_wrong_neutral_citation_for_real_case() -> None:
    item = await _item("Arnesh Kumar v. State of Bihar, 2014 INSC 999.")
    assert item["status"] == "citation_differs"
    assert item["supreme_court_matches"][0]["neutral_citation"] == "2014 INSC 463"


@pytest.mark.asyncio
async def test_scr_citation_of_another_case_is_error() -> None:
    item = await _item("Fake Traders v. Mehta, [2014] 8 S.C.R. 128.")
    assert item["status"] == "name_differs"
    assert item["severity"] == "error"
    assert "ARNESH KUMAR" in item["supreme_court_matches"][0]["title"]


@pytest.mark.asyncio
async def test_ambiguous_name_lists_possible_matches() -> None:
    item = await _item("Reliance is placed on Vidya Drolia v. Durga Trading Corporation.")
    assert item["status"] == "possible_matches"
    assert len(item["supreme_court_matches"]) >= 2


@pytest.mark.asyncio
async def test_not_found_message_mentions_coverage() -> None:
    item = await _item("Ramesh Textiles v. Union of India, (2019) 7 SCC 412.")
    assert item["status"] == "not_found"
    assert "High Court judgments are not included yet" in item["message"]


# ── Judgment Finder API ─────────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    token = create_access_token(
        {"sub": "legal-user-jf", "email": "jf@example.com", "role": "tenant_admin", "tenant_id": "tenant-a"}
    )
    return {"Authorization": f"Bearer {token}", "X-App-Key": "legalmitra"}


def test_judgment_search_requires_login() -> None:
    assert TestClient(app).get("/api/v1/legalmitra/judgments/search?q=Arnesh").status_code == 401


def test_judgment_search_by_party_and_citation() -> None:
    client = TestClient(app)
    by_name = client.get(
        "/api/v1/legalmitra/judgments/search", params={"q": "Arnesh Kumar v. State of Bihar"}, headers=_headers()
    ).json()
    assert by_name["results"][0]["neutral_citation"] == "2014 INSC 463"
    assert "CC BY 4.0" in by_name["attribution"]

    by_cite = client.get(
        "/api/v1/legalmitra/judgments/search", params={"q": "2021 INSC 469"}, headers=_headers()
    ).json()
    assert by_cite["count"] == 1
    assert by_cite["results"][0]["pdf_url"].startswith("https://indian-supreme-court-judgments.s3.amazonaws.com/")

    by_word = client.get(
        "/api/v1/legalmitra/judgments/search", params={"q": "Puttaswamy", "year": 2017}, headers=_headers()
    ).json()
    assert any(r["neutral_citation"] == "2017 INSC 801" for r in by_word["results"])
