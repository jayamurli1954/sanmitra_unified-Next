"""Citation Checker — verify every authority in a draft or the other side's papers.

Deterministic, no model generation. For each authority found in the text:

* Cases (names and law-report citations) are matched against LegalMitra's
  curated judgment records and, optionally, the firm's own library (RAG).
* Criminal-code sections (IPC / CrPC / Evidence Act and BNS / BNSS / BSA) are
  checked for existence (section range) and mapped through the curated
  IPC→BNS / CrPC→BNSS / IEA→BSA crosswalk. Explicit "old (now new)" pairs are
  validated against the crosswalk, including documented false mappings.

"Not found" means not found in LegalMitra's sources — never that a case is
fake. The tool cannot yet tell whether a judgment was later overruled.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Awaitable, Callable

from app.modules.legal_compat import code_crosswalk as cx
from app.modules.legal_compat import sc_judgment_index as sc_index
from app.modules.legal_compat.case_citation_audit import (
    case_name_matches,
    find_case_claims,
    reporter_matches,
)

MAX_TEXT_CHARS = 300_000
MAX_LIBRARY_LOOKUPS = 15

NEW_CODES_COMMENCEMENT = "1 July 2024"

ADVISORY = (
    "Citation Checker compares authorities against LegalMitra's curated sources and your "
    "library. 'Not found' means not in these sources — not that the authority is wrong. "
    "Later treatment (overruled, reversed, distinguished) is not yet checked. Verify every "
    "authority against the reported judgment or Bare Act before filing."
)

# ── Case sources ───────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def curated_judgments() -> tuple[dict[str, Any], ...]:
    """Curated judgment records (constitutional landmarks + GST §54 digests)."""
    from app.modules.legal_compat.constitutional_seed import iter_judgment_records
    from app.modules.legal_compat.judgment_retrieval import _load_corpus

    rows: list[dict[str, Any]] = []
    try:
        rows.extend(iter_judgment_records())
    except (OSError, ValueError):
        pass
    try:
        rows.extend(_load_corpus("cgst_section_54"))
    except (OSError, ValueError):
        pass
    return tuple(rows)


def _record_citations(record: dict[str, Any]) -> list[str]:
    out = [str(record.get("citation") or "")]
    out.extend(str(c) for c in record.get("alternative_citations") or [])
    return [c for c in out if c.strip()]


def _record_name_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(k) or "") for k in ("title", "petitioner", "respondent")
    )


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    treatment = [str(t) for t in record.get("overruled_or_modified") or [] if str(t).strip()]
    return {
        "title": record.get("title"),
        "citation": record.get("citation"),
        "alternative_citations": list(record.get("alternative_citations") or []),
        "court_name": record.get("court_name"),
        "year": record.get("year"),
        "source": record.get("_seed_file") or "curated",
        "treatment_notes": treatment,
    }


def _match_curated(name: str | None, citation: str | None) -> dict[str, Any]:
    """Match against hand-curated records (carry SCC citations and treatment notes)."""
    records = curated_judgments()
    by_name = [r for r in records if name and case_name_matches(name, _record_name_text(r))]
    by_citation = [
        r
        for r in records
        if citation and any(reporter_matches(citation, c) for c in _record_citations(r))
    ]

    if name and citation:
        both = [r for r in by_name if r in by_citation]
        if both:
            return {"status": "verified", "record": both[0]}
        if by_name:
            return {"status": "citation_differs", "record": by_name[0]}
        if by_citation:
            return {"status": "name_differs", "record": by_citation[0]}
    elif name and by_name:
        return {"status": "verified", "record": by_name[0]}
    elif citation and by_citation:
        return {"status": "verified", "record": by_citation[0]}
    return {"status": "not_found", "record": None}


def _match_supreme_court(name: str | None, citation: str | None) -> dict[str, Any]:
    """Match against the Supreme Court open-data index (neutral + SCR citations)."""
    index = sc_index.get_index()
    if not len(index):
        return {"status": "not_found", "sc": []}
    year = sc_index.citation_year(citation)
    held = bool(citation) and sc_index.is_held_reporter(citation)

    if held:
        row = index.by_citation(citation)
        if row:
            if not name or index.name_matches(name, row):
                return {"status": "verified", "sc": [row]}
            return {"status": "name_differs", "sc": [row]}
        if name:
            candidates = index.by_name(name, year=year)
            if candidates:
                return {"status": "citation_differs", "sc": candidates[:3]}
        return {"status": "not_found", "sc": []}

    if not name:
        return {"status": "not_found", "sc": []}
    candidates = index.by_name(name, year=year)
    if len(candidates) == 1:
        return {"status": "found_sc" if citation else "verified", "sc": candidates}
    if candidates:
        return {"status": "possible_matches", "sc": candidates[:3]}
    return {"status": "not_found", "sc": []}


def _match_case(name: str | None, citation: str | None) -> dict[str, Any]:
    curated = _match_curated(name, citation)
    sc = _match_supreme_court(name, citation)
    # A hand-curated verdict wins, except "not found" — then use the SC index.
    if curated["status"] != "not_found":
        # Attach the SC record (for its PDF link) when it is the same case.
        same = [r for r in sc.get("sc") or [] if sc["status"] in {"verified", "found_sc"}]
        return {**curated, "sc": same}
    return {"status": sc["status"], "record": None, "sc": sc.get("sc") or []}


def _group_authorities(text: str) -> list[dict[str, Any]]:
    """Pair each case name with the law-report citation that directly follows it."""
    claims = find_case_claims(text)
    names = [c for c in claims if c["claim_type"] == "case_name"]
    reporters = [c for c in claims if c["claim_type"] == "reporter_citation"]
    used: set[int] = set()
    out: list[dict[str, Any]] = []
    for n in names:
        attached = None
        for i, r in enumerate(reporters):
            if i in used or r["start"] < n["end"]:
                continue
            gap = text[n["end"] : r["start"]]
            # Punctuation only, or the tail of a party name that contains a comma
            # ("Home Secretary, State of Bihar, (1980) 1 SCC 81").
            if re.fullmatch(r"[\s,;:()\[\]*_]*", gap) or (
                len(gap) <= 60
                and gap.lstrip().startswith(",")
                and not re.search(r"[.;]\s|\sv\.?\s|\svs\.?\s|\n", gap)
            ):
                attached = r
                used.add(i)
            break
        out.append(
            {
                "name": n["text"],
                "citation": attached["text"] if attached else None,
                "start": n["start"],
                "end": attached["end"] if attached else n["end"],
            }
        )
    for i, r in enumerate(reporters):
        if i not in used:
            out.append({"name": None, "citation": r["text"], "start": r["start"], "end": r["end"]})
    out.sort(key=lambda a: a["start"])
    return out


_CASE_MESSAGES = {
    "verified": "Found in LegalMitra's judgment records.",
    "found_sc": (
        "Found in Supreme Court records. SCC / AIR page citations are not in our data, "
        "so the page citation itself was not checked — confirm it in the law report."
    ),
    "possible_matches": (
        "Several Supreme Court judgments match this name. Add the year or citation, "
        "or pick the right one below."
    ),
    "citation_differs": (
        "Case found, but the citation given does not match our record. "
        "It may be a parallel citation we do not hold, or a wrong citation — check the law report."
    ),
    "name_differs": (
        "This citation belongs to a different case in our records. "
        "The case name or the citation is likely wrong."
    ),
    "found_in_library": "Found in your LegalMitra library (uploaded / ingested documents).",
    "not_found": (
        "Not found in LegalMitra's sources (curated records and Supreme Court judgments since 1950; "
        "High Court judgments are not included yet). This does not mean the case is fake — "
        "verify it against the reported judgment before relying on it."
    ),
}

_CASE_SEVERITY = {
    "verified": "ok",
    "found_sc": "ok",
    "found_in_library": "ok",
    "possible_matches": "info",
    "citation_differs": "warning",
    "not_found": "warning",
    "name_differs": "error",
}

# ── Criminal-code statute references ──────────────────────────────────────

# Highest section number in each code (as enacted, ignoring lettered inserts).
_CODE_MAX_SECTION = {"IPC": 511, "CrPC": 484, "IEA": 167, "BNS": 358, "BNSS": 531, "BSA": 170}
_LEGACY_TO_NEW = {"IPC": "BNS", "CrPC": "BNSS", "IEA": "BSA"}
_NEW_TO_LEGACY = {v: k for k, v in _LEGACY_TO_NEW.items()}
_CODE_LABEL = {
    "IPC": "Indian Penal Code, 1860",
    "CrPC": "Code of Criminal Procedure, 1973",
    "IEA": "Indian Evidence Act, 1872",
    "BNS": "Bharatiya Nyaya Sanhita, 2023",
    "BNSS": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "BSA": "Bharatiya Sakshya Adhiniyam, 2023",
}

_CODE_ALT = (
    r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|Bharatiya\s+Nyaya\s+Sanhita|"
    r"Bharatiya\s+Sakshya\s+Adhiniyam|Indian\s+Penal\s+Code|Code\s+of\s+Criminal\s+Procedure|"
    r"(?:Indian\s+)?Evidence\s+Act|BNSS|BNS|BSA|I\.?\s?P\.?\s?C\.?|Cr\.?\s?P\.?\s?C\.?|IEA"
)
_SEC = r"\d{1,3}[A-Z]{0,2}(?:\(\d+[A-Za-z]?\))*"
_SEC_LIST = rf"{_SEC}(?:\s*(?:,|/|&|and|r/w|read\s+with)\s*{_SEC})*"
_SEC_WORD = r"(?:Sections?|Secs?\.?|Ss\.|S\.|u/s\.?|U/[Ss]\.?)"

# "Section 420 IPC", "Sections 406, 420 and 120B of the Indian Penal Code", "u/s 482 CrPC"
_STATUTE_A = re.compile(
    rf"{_SEC_WORD}\s*(?P<secs>{_SEC_LIST})\s*(?:,\s*)?(?:of\s+(?:the\s+)?)?(?P<code>{_CODE_ALT})(?![A-Za-z])",
)
# "IPC 420", "BNSS s. 528", "Cr.P.C. Section 482"
_STATUTE_B = re.compile(
    rf"(?<![A-Za-z])(?P<code>{_CODE_ALT})\s*,?\s*(?:{_SEC_WORD}\s*)?(?P<secs>{_SEC_LIST})(?![\d])",
)


def _canonical_code(raw: str) -> str | None:
    flat = re.sub(r"[\s.]", "", raw).lower()
    if flat in {"ipc", "indianpenalcode"}:
        return "IPC"
    if flat in {"crpc", "codeofcriminalprocedure"}:
        return "CrPC"
    if flat in {"iea", "evidenceact", "indianevidenceact"}:
        return "IEA"
    if flat in {"bns", "bharatiyanyayasanhita"}:
        return "BNS"
    if flat in {"bnss", "bharatiyanagariksurakshasanhita"}:
        return "BNSS"
    if flat in {"bsa", "bharatiyasakshyaadhiniyam"}:
        return "BSA"
    return cx.normalize_code(raw)


def _split_sections(secs: str) -> list[str]:
    parts = re.split(r"\s*(?:,|/|&|\band\b|r/w|read\s+with)\s*", secs)
    return [p.strip() for p in parts if p.strip()]


def _base_section(section: str) -> str:
    return re.sub(r"\(.*$", "", section).strip().upper()


def _section_number(section: str) -> int | None:
    m = re.match(r"\d+", section)
    return int(m.group(0)) if m else None


def find_statute_refs(text: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for pattern in (_STATUTE_A, _STATUTE_B):
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if any(s <= span[0] < e or s < span[1] <= e for s, e in seen):
                continue
            code = _canonical_code(m.group("code"))
            if not code or code not in _CODE_MAX_SECTION:
                continue
            sections = _split_sections(m.group("secs"))
            # "IPC 1860" / "BNSS 2023" are Act years, not sections.
            if pattern is _STATUTE_B and len(sections) == 1 and re.fullmatch(r"(18|19|20)\d\d", sections[0]):
                continue
            seen.add(span)
            for section in sections:
                refs.append(
                    {"code": code, "section": section, "text": m.group(0).rstrip(" .,;:"), "start": m.start(), "end": m.end()}
                )
    refs.sort(key=lambda r: (r["start"], r["section"]))
    return refs


def _check_statute(ref: dict[str, Any]) -> dict[str, Any]:
    code, section = ref["code"], ref["section"]
    number = _section_number(section)
    item: dict[str, Any] = {
        "kind": "statute",
        "text": ref["text"],
        "code": code,
        "code_label": _CODE_LABEL[code],
        "section": section,
    }
    if number is None or number < 1 or number > _CODE_MAX_SECTION[code]:
        item.update(
            status="section_not_in_code",
            severity="error",
            message=(
                f"{_CODE_LABEL[code]} has no Section {section} "
                f"(it ends at Section {_CODE_MAX_SECTION[code]})."
            ),
        )
        return item

    if code in _LEGACY_TO_NEW:
        result = cx.lookup(from_code=code, section=section, direction="forward")
        if not result.get("found") and _base_section(section) != section.upper():
            result = cx.lookup(from_code=code, section=_base_section(section), direction="forward")
        matches = result.get("matches") or []
        targets = sorted({f"{m.get('to_code')} {m.get('to_section')}" for m in matches})
        item["equivalents"] = targets
        if targets:
            item.update(
                status="old_code",
                severity="info",
                message=(
                    f"Old code. Current equivalent: {', '.join(targets)}. "
                    f"Offences/proceedings on or after {NEW_CODES_COMMENCEMENT} generally fall "
                    "under the new code; earlier ones remain under the old code (check savings clauses)."
                ),
            )
        else:
            item.update(
                status="old_code_unmapped",
                severity="warning",
                message=(
                    f"Old code. No mapping in LegalMitra's curated crosswalk — find the "
                    f"{_LEGACY_TO_NEW[code]} equivalent in the Bare Act; do not guess."
                ),
            )
        return item

    result = cx.lookup(from_code=code, section=section, direction="reverse")
    if not result.get("found") and _base_section(section) != section.upper():
        result = cx.lookup(from_code=code, section=_base_section(section), direction="reverse")
    previous = sorted({f"{m.get('from_code')} {m.get('from_section')}" for m in result.get("matches") or []})
    item["equivalents"] = previous
    item.update(
        status="new_code",
        severity="ok",
        message=(
            f"Current code. Corresponds to {', '.join(previous)}." if previous
            else "Current code. No old-code predecessor in the curated crosswalk."
        ),
    )
    return item


def _check_mapping_pairs(text: str, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate explicit old→new pairs such as "Section 420 IPC (now Section 318(4) BNS)"."""
    pairs: list[dict[str, Any]] = []
    for old in refs:
        if old["code"] not in _LEGACY_TO_NEW:
            continue
        # Only the reference immediately after this one, joined by a short connector:
        # "Section 420 IPC (now Section 318(4) BNS)", "IPC 302 / BNS 103".
        following = [r for r in refs if r["start"] >= old["end"]]
        if not following:
            continue
        new = following[0]
        if new["code"] != _LEGACY_TO_NEW[old["code"]]:
            continue
        # A multi-section reference ("Sections 406, 420 IPC") pairs only its last section.
        same_span = [r for r in refs if r["start"] == old["start"]]
        if same_span and same_span[-1] is not old:
            continue
        between = text[old["end"] : new["start"]].lower()
        if len(between) > 30 or re.search(r"[.;]\s|\n", between):
            continue
        if not re.search(r"now|new|correspond|equivalent|replaced|i\.e\.|\(|→|->|=|/", between):
            continue
        false = cx.detect_false_mapping(
            from_code=old["code"], from_section=old["section"],
            to_code=new["code"], to_section=new["section"],
        )
        forward = cx.lookup(from_code=old["code"], section=_base_section(old["section"]), direction="forward")
        ok = any(
            str(m.get("to_code")) == new["code"]
            and (
                cx.sections_compatible(str(m.get("to_section")), new["section"])
                or _base_section(str(m.get("to_section"))) == _base_section(new["section"])
            )
            for m in forward.get("matches") or []
        )
        targets = sorted({f"{m.get('to_code')} {m.get('to_section')}" for m in forward.get("matches") or []})
        claimed = f"{old['code']} {old['section']} → {new['code']} {new['section']}"
        if false:
            status, severity = "mapping_wrong", "error"
            message = f"Known wrong mapping. {false.get('reason') or ''}".strip()
            if targets:
                message += f" Curated equivalent: {', '.join(targets)}."
        elif ok:
            status, severity, message = "mapping_ok", "ok", "Mapping matches the curated crosswalk."
        elif targets:
            status, severity = "mapping_wrong", "error"
            message = f"Does not match the curated crosswalk, which maps it to {', '.join(targets)}."
        else:
            status, severity = "mapping_unverified", "warning"
            message = "Old section not in the curated crosswalk; verify the mapping in the Bare Act."
        pairs.append(
            {"kind": "mapping", "text": claimed, "status": status, "severity": severity, "message": message}
        )
    return pairs


# ── Public API ─────────────────────────────────────────────────────────────

LibraryLookup = Callable[[str], Awaitable[list[dict[str, Any]]]]


def _library_evidence(citation: dict[str, Any]) -> str:
    from app.modules.legal_compat.case_citation_audit import case_evidence_blob

    return case_evidence_blob([citation])


async def check_citations(
    text: str,
    *,
    library_lookup: LibraryLookup | None = None,
) -> dict[str, Any]:
    """Check every case and criminal-code authority in ``text``.

    ``library_lookup(query)`` may return RAG citations from the firm's own
    library; used only for cases not found in curated records.
    """
    body = (text or "")[:MAX_TEXT_CHARS]
    items: list[dict[str, Any]] = []
    lookups = 0
    library_unavailable = False

    for authority in _group_authorities(body):
        name, citation = authority["name"], authority["citation"]
        match = _match_case(name, citation)
        status = match["status"]
        if status == "not_found" and name and library_lookup and lookups < MAX_LIBRARY_LOOKUPS:
            lookups += 1
            try:
                hits = await library_lookup(name)
            except Exception:  # library is best-effort; never fail the check
                hits = []
                library_lookup = None  # stop after the first failure / timeout
                library_unavailable = True
            for hit in hits or []:
                evidence = _library_evidence(hit)
                if case_name_matches(name, evidence) and (
                    not citation or reporter_matches(citation, evidence)
                ):
                    status = "found_in_library"
                    match = {"status": status, "record": None, "library_title": hit.get("title")}
                    break
        record = match.get("record")
        item = {
            "kind": "case",
            "text": body[authority["start"] : authority["end"]],
            "case_name": name,
            "citation": citation,
            "status": status,
            "severity": _CASE_SEVERITY[status],
            "message": _CASE_MESSAGES[status],
            "matched_record": _record_summary(record) if record else None,
        }
        item["supreme_court_matches"] = [sc_index.public_record(r) for r in match.get("sc") or []]
        if match.get("library_title"):
            item["library_title"] = match["library_title"]
        if record and _record_summary(record)["treatment_notes"]:
            item["message"] += " Our record has a treatment note — read it before relying on this case."
        items.append(item)

    refs = find_statute_refs(body)
    seen_sections: set[tuple[str, str]] = set()
    for ref in refs:
        key = (ref["code"], ref["section"].upper())
        if key in seen_sections:
            continue
        seen_sections.add(key)
        items.append(_check_statute(ref))
    items.extend(_check_mapping_pairs(body, refs))

    counts: dict[str, int] = {"ok": 0, "info": 0, "warning": 0, "error": 0}
    for item in items:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1

    return {
        "items": items,
        "summary": {
            "total": len(items),
            "cases": sum(1 for i in items if i["kind"] == "case"),
            "statutes": sum(1 for i in items if i["kind"] == "statute"),
            "mappings": sum(1 for i in items if i["kind"] == "mapping"),
            **counts,
        },
        "truncated": len(text or "") > MAX_TEXT_CHARS,
        "curated_judgment_count": len(curated_judgments()),
        "supreme_court_index_count": len(sc_index.get_index()),
        "attribution": sc_index.ATTRIBUTION,
        "library_unavailable": library_unavailable,
        "advisory": ADVISORY,
        "human_review_required": True,
    }


# ── File text extraction ───────────────────────────────────────────────────


class UnsupportedDocumentError(ValueError):
    pass


def extract_document_text(filename: str, payload: bytes) -> str:
    """Extract plain text from PDF, DOCX or TXT uploads (no OCR)."""
    name = (filename or "").lower()
    if name.endswith(".pdf") or payload[:5] == b"%PDF-":
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(payload))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        import zipfile
        from io import BytesIO

        from app.modules.legal_compat.safe_xml import fromstring

        with zipfile.ZipFile(BytesIO(payload)) as zf:
            info = zf.getinfo("word/document.xml")
            if info.file_size > 50 * 1024 * 1024:
                raise UnsupportedDocumentError("DOCX content is too large.")
            root = fromstring(zf.read(info))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        for para in root.iter(f"{ns}p"):
            paragraphs.append("".join(t.text or "" for t in para.iter(f"{ns}t")))
        return "\n".join(paragraphs)
    if name.endswith((".txt", ".md")):
        return payload.decode("utf-8", errors="ignore")
    raise UnsupportedDocumentError("Upload a PDF, DOCX or TXT file.")
