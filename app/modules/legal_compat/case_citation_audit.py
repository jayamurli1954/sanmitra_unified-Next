"""Case-citation gate: case authorities must come from retrieved sources.

The statute audit (``citation_audit``) only checks section numbers. Model output
can still name Indian cases and law-report citations from memory, e.g.
"Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225". Until LegalMitra has
a real case citator, the only trustworthy rule is: a case may be cited only if it
appears in the retrieved / authorized citation evidence.

Unsupported case names and reporter citations are redacted in place (not the
whole answer — statutory analysis stays useful) and recorded as claims.
Pattern-only, deterministic; no third-party code.
"""
from __future__ import annotations

import re
from typing import Any

REDACTION_MARKER = "[case citation removed: not found in retrieved sources]"

# ── Detection ────────────────────────────────────────────────────────────────

# A party word: Capitalised token (allows dots/&/'/- such as "U.P.", "Ltd.",
# "M/s") or a short parenthetical like "(India)" / "(P)".
_WORD = r"(?:[A-Z][A-Za-z0-9&'./\-]*|\([A-Za-z.\s]{1,15}\))"
_CONNECT = r"(?:of|the|and|for|in|&|de|da|du)"
_PARTY = rf"{_WORD}(?:\s+(?:{_CONNECT}\s+)?{_WORD}){{0,8}}"
_SEP = r"(?:v\.?|vs\.?|Vs\.?|V/s\.?|versus|Versus)"

CASE_NAME_RE = re.compile(rf"(?<![A-Za-z])(?P<left>{_PARTY})\s+{_SEP}\s+(?P<right>{_PARTY})")

# Indian law-report citations.
_REPORTER = (
    r"SCC\s+OnLine\s+[A-Z][A-Za-z]*|SCC\s*\(\w+\)|SCC|SCR|S\.C\.R\.|SCALE|JT|AIR\s+\w+|"
    r"ITR|GSTL|STC|TMI|Taxman|taxmann\.com|ELT|E\.L\.T\.|CTR|ITD|SOT|Comp\s+Cas|"
    r"Cri\s*LJ|Cr\.?L\.?J\.?|ALL\s?ER|DLT|Bom\s*LR|MLJ|KLT|ILR"
)
REPORTER_RE = re.compile(
    rf"(?:"
    # (1973) 4 SCC 225 / [2021] 3 SCR 1 / (2017) 52 GSTL 513 (SC) / 1992 Supp (1) SCC 335
    rf"[\(\[]\d{{4}}[\)\]]\s*(?:Supp\.?\s*)?(?:\(\d+\)\s*)?\d*\s*(?:{_REPORTER})\s*\d+(?:\s*\((?:SC|[A-Z][a-z]{{0,5}}\.?)\))?"
    # AIR 1973 SC 1461
    rf"|AIR\s+\d{{4}}\s+[A-Z][A-Za-z]*\s+\d+"
    # 2021 SCC OnLine SC 706 / 1992 Supp (1) SCC 335 / 2022 (5) TMI 123
    rf"|\b\d{{4}}\s+(?:Supp\.?\s*)?(?:\(\d+\)\s*)?(?:{_REPORTER})\s*\d+"
    rf")"
)

# Leading words that start a sentence but are not part of a party name.
_LEAD_STOP = {
    "in", "see", "the", "also", "per", "following", "as", "held", "under", "relying",
    "cf", "cf.", "e.g.", "i.e.", "and", "but", "while", "where", "when", "thus", "hence",
    "however", "therefore", "accordingly", "notably", "similarly", "key", "case",
    "leading", "authority", "authorities", "judgment", "decision", "ruling", "court",
}

_ABBREV_DOT = {"ltd.", "pvt.", "co.", "inc.", "anr.", "ors.", "bros.", "corpn.", "u.p.", "m.p.", "jr.", "sr."}

# Tokens too generic to identify a case.
_GENERIC_TOKENS = {
    "of", "the", "and", "for", "in", "de", "da", "du", "union", "india", "state", "states",
    "government", "govt", "commissioner", "commr", "cit", "deputy", "assistant", "joint",
    "chief", "officer", "income", "tax", "central", "excise", "customs", "gst", "service",
    "ltd", "limited", "pvt", "private", "p", "co", "company", "corporation", "corpn",
    "inc", "llp", "bros", "anr", "ors", "another", "others", "m/s", "ms", "mr", "mrs",
    "sri", "shri", "smt", "dr", "air", "scc", "scr", "sc", "hc", "online", "supp",
    "secretary", "director", "general", "authority", "board", "bank", "national",
    "municipal", "registrar", "collector", "district", "regional", "high", "court",
    "supreme", "in re", "re",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:/[a-z0-9]+)?", text.lower())


def _distinctive(text: str) -> list[str]:
    out: list[str] = []
    for tok in _tokens(text):
        if tok in _GENERIC_TOKENS or len(tok) < 2 or tok.isdigit():
            continue
        if tok not in out:
            out.append(tok)
    return out


def _reporter_tokens(text: str) -> list[str]:
    """Alphanumeric tokens; "2022 (2) SCC 603" == "(2022) 2 SCC 603"."""
    return re.findall(r"[a-z]+|\d+", (text or "").lower())


def _contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    if not n or n > len(haystack):
        return False
    return any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


def _trim_case_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Drop sentence lead-ins ("In", "See") and a sentence-final full stop."""
    # A party never spans a sentence boundary: "...the Constitution. State of X v. Y".
    sep = re.search(rf"\s{_SEP}\s", text[start:end])
    origin = start
    left_end = origin + (sep.start() if sep else 0)
    for wm in re.finditer(r"\S+", text[origin:left_end]):
        low = wm.group(0).lower()
        if (
            low.endswith(".")
            and len(low) > 4
            and low not in _ABBREV_DOT
            and not re.fullmatch(r"(?:[a-z]\.)+", low)
            and origin + wm.end() < left_end
        ):
            start = origin + wm.end()
    while start < end and text[start].isspace():
        start += 1
    while True:
        m = re.match(r"\s*(\S+)\s+", text[start:end])
        if not m:
            break
        word = m.group(1).lower().strip("*_:,;")
        if word in _LEAD_STOP:
            start += m.end()
            continue
        break
    span = text[start:end]
    if span.endswith("."):
        last = span.split()[-1].lower()
        if last not in _ABBREV_DOT and not re.fullmatch(r"(?:[a-z]\.)+", last):
            end -= 1
    return start, end


def find_case_claims(text: str) -> list[dict[str, Any]]:
    """Return case-name and reporter-citation mentions with spans."""
    if not text:
        return []
    claims: list[dict[str, Any]] = []
    for m in CASE_NAME_RE.finditer(text):
        start, end = _trim_case_span(text, m.start(), m.end())
        span = text[start:end]
        # Need at least one distinctive token to be a case name at all.
        if not _distinctive(span):
            continue
        claims.append({"claim_type": "case_name", "text": span, "start": start, "end": end})
    for m in REPORTER_RE.finditer(text):
        claims.append(
            {"claim_type": "reporter_citation", "text": m.group(0), "start": m.start(), "end": m.end()}
        )
    claims.sort(key=lambda c: (c["start"], -c["end"]))
    return claims


# ── Evidence ────────────────────────────────────────────────────────────────


def case_evidence_blob(citations: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for citation in citations or []:
        if not isinstance(citation, dict):
            continue
        for key in ("title", "reference", "snippet", "text", "source_uri", "citation", "case_name"):
            value = citation.get(key)
            if value:
                parts.append(str(value))
        meta = citation.get("legal_metadata") or {}
        if isinstance(meta, dict):
            for key in ("case_name", "citation", "title", "court_name", "parties"):
                value = meta.get(key)
                if value:
                    parts.append(str(value))
            for alt in meta.get("alternative_citations") or []:
                parts.append(str(alt))
    return "\n".join(parts)


def case_name_matches(name: str, evidence_text: str) -> bool:
    """True when the distinctive parts of a case name appear in evidence_text."""
    return _case_name_supported(name, set(_tokens(evidence_text)))


def reporter_matches(citation: str, evidence_text: str) -> bool:
    """True when the citation's token sequence appears whole in evidence_text."""
    return _reporter_supported(citation, _reporter_tokens(evidence_text))


def _case_name_supported(name: str, evidence_tokens: set[str]) -> bool:
    distinctive = _distinctive(name)
    if not distinctive or not evidence_tokens:
        return False
    hits = sum(1 for tok in distinctive if tok in evidence_tokens)
    return hits >= max(1, -(-len(distinctive) * 2 // 3))  # ceil(2/3)


def _reporter_supported(citation: str, evidence_seq: list[str]) -> bool:
    return _contains_sequence(evidence_seq, _reporter_tokens(citation))


# ── Audit + redaction ───────────────────────────────────────────────────────


def audit_case_citations(
    *,
    response_text: str,
    citations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Classify each case mention as verified or unsupported."""
    claims = find_case_claims(response_text or "")
    evidence = case_evidence_blob(citations)
    evidence_tokens = set(_tokens(evidence))
    evidence_seq = _reporter_tokens(evidence)

    out: list[dict[str, Any]] = []
    verified = unsupported = 0
    for claim in claims:
        if claim["claim_type"] == "case_name":
            ok = _case_name_supported(claim["text"], evidence_tokens)
        else:
            ok = _reporter_supported(claim["text"], evidence_seq)
        outcome = "verified" if ok else "unsupported"
        if ok:
            verified += 1
        else:
            unsupported += 1
        out.append({**claim, "outcome": outcome})

    return {
        "claim_count": len(out),
        "verified_count": verified,
        "unsupported_count": unsupported,
        "claims": out,
    }


def _merge_spans(spans: list[tuple[int, int]], text: str) -> list[tuple[int, int]]:
    """Merge overlapping spans and spans separated only by punctuation/space."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged:
            p_start, p_end = merged[-1]
            gap = text[p_end:start] if start > p_end else ""
            if start <= p_end or re.fullmatch(r"[\s,;:()\[\]*_\-–—]*", gap):
                merged[-1] = (p_start, max(p_end, end))
                continue
        merged.append((start, end))
    return merged


def redact_unsupported_case_citations(
    *,
    response_text: str,
    citations: list[dict[str, Any]] | None,
) -> tuple[str, dict[str, Any]]:
    """Return (redacted_text, audit). Verified authorities are left untouched.

    A reporter citation attached to an unsupported case name is removed with it,
    even if the bare citation string happens to appear in evidence.
    """
    audit = audit_case_citations(response_text=response_text, citations=citations)
    if not audit["unsupported_count"]:
        return response_text, audit

    text = response_text
    bad = [(c["start"], c["end"]) for c in audit["claims"] if c["outcome"] == "unsupported"]
    merged = _merge_spans(bad, text)
    # Absorb a directly-following reporter citation into a removed case name
    # ("X v. Y, (2020) 1 SCC 1"), and trailing markdown emphasis.
    reporters = [(c["start"], c["end"]) for c in audit["claims"] if c["claim_type"] == "reporter_citation"]
    expanded: list[tuple[int, int]] = []
    for start, end in merged:
        for r_start, r_end in reporters:
            if r_start >= end and re.fullmatch(r"[\s,;:()\[\]*_]*", text[end:r_start]):
                end = max(end, r_end)
        # Swallow wrapping emphasis markers (*Name*, **Name**).
        while start > 0 and text[start - 1] in "*_" and end < len(text) and text[end] in "*_":
            start -= 1
            end += 1
        expanded.append((start, end))
    merged = _merge_spans(expanded, text)

    pieces: list[str] = []
    cursor = 0
    for start, end in merged:
        pieces.append(text[cursor:start])
        pieces.append(REDACTION_MARKER)
        cursor = end
    pieces.append(text[cursor:])
    redacted = "".join(pieces)
    audit["redacted_count"] = len(merged)
    return redacted, audit
