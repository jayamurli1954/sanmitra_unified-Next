"""Stage 2.1 statute-first citation audit (pattern only; no third-party code).

Compares statute section numbers mentioned in the answer against retrieved /
authorized citation text. Outcomes: verified | mismatch | unverifiable.
"""
from __future__ import annotations

import re
from typing import Any

# "Section 54", "Sec. 139", "s. 54", "§54", "CGST s.54" style mentions.
_SECTION_CLAIM_RE = re.compile(
    r"(?:section|sec\.?|§)\s*(\d+[A-Za-z]?)|"
    r"\bs\.?\s*(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)


def _text_for_claim_extraction(text: str) -> str:
    """Drop verifier caution blocks so normalized wrong-section mentions are not re-audited."""
    if not text:
        return ""
    # Remove markdown caution / statute-verification callouts appended by normalizers.
    cleaned = re.sub(
        r"(?is)(?:>\s*)?\[!CAUTION\].*?(?=\n\n[^>]|\Z)",
        " ",
        text,
    )
    cleaned = re.sub(
        r"(?is)\*\*Statute Verification:\*\*.*?(?=\n\n|\Z)",
        " ",
        cleaned,
    )
    return cleaned


def extract_section_numbers(text: str) -> list[str]:
    """Return unique statute section tokens mentioned in text (order preserved)."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _SECTION_CLAIM_RE.finditer(_text_for_claim_extraction(text)):
        token = (match.group(1) or match.group(2) or "").strip()
        if not token:
            continue
        key = token.upper()
        if key in seen:
            continue
        seen.add(key)
        found.append(token)
    return found


def _citation_evidence_blob(citations: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for citation in citations or []:
        if not isinstance(citation, dict):
            continue
        meta = citation.get("legal_metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        for key in (
            "title",
            "reference",
            "snippet",
            "source_uri",
            "document_id",
            "chunk_id",
        ):
            value = citation.get(key)
            if value:
                parts.append(str(value))
        for key in ("act", "act_name", "section", "citation", "title"):
            value = meta.get(key)
            if value:
                parts.append(str(value))
    return "\n".join(parts)


def _section_supported(section: str, evidence: str) -> bool:
    if not evidence:
        return False
    # Word-ish boundary around the section token inside evidence text.
    pattern = re.compile(
        rf"(?:section|sec\.?|s\.?|§)\s*{re.escape(section)}\b|"
        rf"\b{re.escape(section)}\b",
        re.IGNORECASE,
    )
    return pattern.search(evidence) is not None


def audit_statute_section_claims(
    *,
    response_text: str,
    citations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audit statute section claims in the answer against citation evidence."""
    sections = extract_section_numbers(response_text)
    evidence = _citation_evidence_blob(list(citations or []))
    claims: list[dict[str, Any]] = []
    verified = mismatch = unverifiable = 0

    for section in sections:
        if not evidence.strip():
            outcome = "unverifiable"
            unverifiable += 1
            evidence_ids: list[Any] = []
        elif _section_supported(section, evidence):
            outcome = "verified"
            verified += 1
            evidence_ids = [
                c.get("chunk_id") or c.get("document_id") or c.get("index")
                for c in (citations or [])
                if isinstance(c, dict) and _section_supported(section, _citation_evidence_blob([c]))
            ]
        else:
            outcome = "mismatch"
            mismatch += 1
            evidence_ids = []

        claims.append(
            {
                "claim_type": "statute_section",
                "section": section,
                "outcome": outcome,
                "evidence_chunk_ids": [eid for eid in evidence_ids if eid is not None],
            }
        )

    return {
        "claim_count": len(claims),
        "verified_count": verified,
        "mismatch_count": mismatch,
        "unverifiable_count": unverifiable,
        "claims": claims,
    }
