"""LegalMitra Citation Checker — cases, criminal-code sections, old→new mappings."""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.main import app
from app.modules.legal_compat import citation_checker as cc
from app.modules.legal_compat import citation_checker_router as ccr
from app.modules.legal_compat.case_citation_audit import reporter_matches


def _by_text(result: dict, fragment: str) -> dict:
    for item in result["items"]:
        if fragment.lower() in item["text"].lower():
            return item
    raise AssertionError(f"no item containing {fragment!r}: {[i['text'] for i in result['items']]}")


async def _check(text: str, **kwargs) -> dict:
    return await cc.check_citations(text, **kwargs)


# ── Cases ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_curated_case_with_matching_citation_is_verified() -> None:
    r = await _check("Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225 settled it.")
    item = _by_text(r, "Kesavananda")
    assert item["status"] == "verified"
    assert item["severity"] == "ok"
    assert item["matched_record"]["citation"] == "(1973) 4 SCC 225"


@pytest.mark.asyncio
async def test_parallel_citation_from_record_is_verified() -> None:
    r = await _check("Hussainara Khatoon v. Home Secretary, State of Bihar, AIR 1979 SC 1360.")
    assert _by_text(r, "Hussainara")["status"] == "verified"


@pytest.mark.asyncio
async def test_real_case_with_wrong_citation_is_flagged() -> None:
    r = await _check("Hussainara Khatoon v. Home Secretary, State of Bihar, (1979) 3 SCC 999.")
    item = _by_text(r, "Hussainara")
    assert item["status"] == "citation_differs"
    assert item["citation"] == "(1979) 3 SCC 999"


@pytest.mark.asyncio
async def test_citation_belonging_to_other_case_is_an_error() -> None:
    r = await _check("Fake Traders v. Mehta, (1973) 4 SCC 225.")
    item = _by_text(r, "Fake Traders")
    assert item["status"] == "name_differs"
    assert item["severity"] == "error"


@pytest.mark.asyncio
async def test_unknown_case_is_not_found_not_called_fake() -> None:
    r = await _check("Ramesh Textiles v. Union of India, (2019) 7 SCC 412.")
    item = _by_text(r, "Ramesh")
    assert item["status"] == "not_found"
    assert item["severity"] == "warning"
    assert "does not mean the case is fake" in item["message"]


@pytest.mark.asyncio
async def test_library_lookup_upgrades_not_found() -> None:
    async def lookup(query: str) -> list[dict]:
        assert "Ramesh Textiles" in query
        return [{"title": "Ramesh Textiles v. Union of India", "snippet": "(2019) 7 SCC 412 — refund"}]

    r = await _check("Ramesh Textiles v. Union of India, (2019) 7 SCC 412.", library_lookup=lookup)
    item = _by_text(r, "Ramesh")
    assert item["status"] == "found_in_library"
    assert item["library_title"] == "Ramesh Textiles v. Union of India"


@pytest.mark.asyncio
async def test_library_failure_is_reported_and_stops_lookups() -> None:
    calls = 0

    async def lookup(_query: str) -> list[dict]:
        nonlocal calls
        calls += 1
        raise TimeoutError

    r = await _check("A Corp v. B Ltd. and C Traders v. D Mills.", library_lookup=lookup)
    assert calls == 1
    assert r["library_unavailable"] is True
    assert all(i["status"] == "not_found" for i in r["items"] if i["kind"] == "case")


@pytest.mark.asyncio
async def test_treatment_note_is_surfaced() -> None:
    r = await _check("I.C. Golaknath v. State of Punjab, AIR 1967 SC 1643.")
    item = _by_text(r, "Golaknath")
    assert item["status"] == "verified"
    assert item["matched_record"]["treatment_notes"]
    assert "treatment note" in item["message"]


def test_reporter_match_requires_whole_tokens() -> None:
    assert reporter_matches("(2021) 2 SCC 1", "(2021) 2 SCC 1")
    assert reporter_matches("2022 (2) SCC 603", "(2022) 2 SCC 603")
    assert not reporter_matches("(2021) 2 SCC 1", "(2021) 2 SCC 112")


# ── Criminal-code sections ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_old_ipc_sections_get_bns_equivalents() -> None:
    r = await _check("Charged under Sections 406, 420 and 120B of the Indian Penal Code.")
    statutes = {i["section"]: i for i in r["items"] if i["kind"] == "statute"}
    assert set(statutes) == {"406", "420", "120B"}
    assert statutes["420"]["status"] == "old_code"
    assert "BNS 318(4)" in statutes["420"]["equivalents"]
    assert "1 July 2024" in statutes["420"]["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "code", "section", "equivalent"),
    [
        ("Petition u/s 482 CrPC.", "CrPC", "482", "BNSS 528"),
        ("Certificate under Section 65B of the Evidence Act.", "IEA", "65B", "BSA 63"),
        ("Cr.P.C. Section 482 applies.", "CrPC", "482", "BNSS 528"),
        ("IPC 420 is invoked.", "IPC", "420", "BNS 318(4)"),
    ],
)
async def test_statute_reference_forms(text: str, code: str, section: str, equivalent: str) -> None:
    r = await _check(text)
    item = next(i for i in r["items"] if i["kind"] == "statute")
    assert (item["code"], item["section"]) == (code, section)
    assert equivalent in item["equivalents"]


@pytest.mark.asyncio
async def test_statute_text_has_no_trailing_full_stop() -> None:
    r = await _check("The complaint invokes Section 999 IPC.")
    assert next(i for i in r["items"] if i["kind"] == "statute")["text"] == "Section 999 IPC"


@pytest.mark.asyncio
async def test_section_beyond_code_is_an_error() -> None:
    r = await _check("The complaint invokes Section 999 IPC.")
    item = next(i for i in r["items"] if i["kind"] == "statute")
    assert item["status"] == "section_not_in_code"
    assert item["severity"] == "error"


@pytest.mark.asyncio
async def test_act_year_is_not_a_section() -> None:
    r = await _check("IPC 1860 was replaced by BNS 2023.")
    assert [i for i in r["items"] if i["kind"] == "statute"] == []


@pytest.mark.asyncio
async def test_new_code_shows_predecessor() -> None:
    r = await _check("Quashing under BNSS Section 528.")
    item = next(i for i in r["items"] if i["kind"] == "statute")
    assert item["status"] == "new_code"
    assert "CrPC 482" in item["equivalents"]


# ── Old → new mapping pairs ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_correct_mapping_pair() -> None:
    r = await _check("Section 420 IPC (now Section 318(4) BNS) applies.")
    pair = next(i for i in r["items"] if i["kind"] == "mapping")
    assert pair["status"] == "mapping_ok"


@pytest.mark.asyncio
async def test_wrong_mapping_pair() -> None:
    r = await _check("Section 302 IPC (now Section 101 BNS) applies.")
    pair = next(i for i in r["items"] if i["kind"] == "mapping")
    assert pair["status"] == "mapping_wrong"
    assert "BNS 103" in pair["message"]


@pytest.mark.asyncio
async def test_known_false_mapping_pair() -> None:
    r = await _check("Section 482 CrPC (now Section 504 BNSS) is invoked.")
    pair = next(i for i in r["items"] if i["kind"] == "mapping")
    assert pair["status"] == "mapping_wrong"
    assert "Known wrong mapping" in pair["message"]
    assert "BNSS 528" in pair["message"]


@pytest.mark.asyncio
async def test_refs_in_different_sentences_are_not_paired() -> None:
    r = await _check("Charged under Section 406 IPC. Later, Section 318(4) BNS was argued.")
    assert [i for i in r["items"] if i["kind"] == "mapping"] == []


@pytest.mark.asyncio
async def test_summary_counts() -> None:
    r = await _check("Section 999 IPC. Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225.")
    assert r["summary"]["error"] == 1
    assert r["summary"]["ok"] == 1
    assert r["human_review_required"] is True


# ── File extraction ─────────────────────────────────────────────────────────


def _docx_bytes(paragraphs: list[str]) -> bytes:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_extract_docx_text() -> None:
    text = cc.extract_document_text("draft.docx", _docx_bytes(["Para one.", "Section 420 IPC."]))
    assert "Section 420 IPC." in text


def test_extract_rejects_unknown_type() -> None:
    with pytest.raises(cc.UnsupportedDocumentError):
        cc.extract_document_text("photo.jpg", b"\xff\xd8\xff")


# ── HTTP ────────────────────────────────────────────────────────────────────


def _auth_headers(tenant_id: str = "tenant-a") -> dict[str, str]:
    token = create_access_token(
        {"sub": "legal-user-cc", "email": "cc@example.com", "role": "tenant_admin", "tenant_id": tenant_id}
    )
    return {"Authorization": f"Bearer {token}", "X-App-Key": "legalmitra"}


def test_citation_check_requires_login() -> None:
    response = TestClient(app).post("/api/v1/legalmitra/citation-check", json={"text": "Section 420 IPC"})
    assert response.status_code == 401


def test_citation_check_rejects_cross_tenant_header() -> None:
    headers = _auth_headers("tenant-a")
    headers["X-Tenant-ID"] = "tenant-b"
    response = TestClient(app).post(
        "/api/v1/legalmitra/citation-check", headers=headers, json={"text": "Section 420 IPC"}
    )
    assert response.status_code == 403


def test_citation_check_text_endpoint() -> None:
    response = TestClient(app).post(
        "/api/v1/legalmitra/citation-check",
        headers=_auth_headers(),
        json={"text": "Section 999 IPC and Section 420 IPC (now Section 318(4) BNS).", "search_library": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["summary"]["error"] == 1
    statuses = {i["status"] for i in body["items"]}
    assert {"section_not_in_code", "old_code", "mapping_ok"} <= statuses


def test_citation_check_upload_docx(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _limits(*_a, **_k):
        return {"max_document_upload_bytes": 5 * 1024 * 1024}

    def _no_library(*_a, **_k):
        async def _lookup(_q: str) -> list[dict]:
            return []

        return _lookup

    monkeypatch.setattr(ccr, "get_usage_limits_for_user", _limits)
    monkeypatch.setattr(ccr, "_library_lookup_for", _no_library)
    payload = _docx_bytes(["Reliance on Fake Traders v. Mehta, (1973) 4 SCC 225."])
    response = TestClient(app).post(
        "/api/v1/legalmitra/citation-check/upload",
        headers=_auth_headers(),
        files={"file": ("reply.docx", payload, "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file_name"] == "reply.docx"
    assert body["items"][0]["status"] == "name_differs"


def test_citation_check_upload_rejects_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _limits(*_a, **_k):
        return {"max_document_upload_bytes": 5 * 1024 * 1024}

    monkeypatch.setattr(ccr, "get_usage_limits_for_user", _limits)
    response = TestClient(app).post(
        "/api/v1/legalmitra/citation-check/upload",
        headers=_auth_headers(),
        files={"file": ("scan.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")},
    )
    assert response.status_code == 415
