"""Corpus-backed judgment retrieval for LegalMitra research (retrieve-or-refuse).

Current: starter curated digests under ``data/legal_seed/gst_section_54_judgments/``.
Used by the Stage 2 offline §54 package when the query asks for referred cases /
judgments. Never invents case names — empty match returns a refuse block.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_SEED_ROOT = _ROOT / "data" / "legal_seed"
_GST54_DIR = _SEED_ROOT / "gst_section_54_judgments"

_CASE_TOKENS = (
    "case",
    "cases",
    "judgment",
    "judgement",
    "judgments",
    "judgements",
    "precedent",
    "referred",
    "citation",
    "authorities",
)


def query_wants_judgments(query: str) -> bool:
    q = " ".join((query or "").strip().lower().split())
    return any(token in q for token in _CASE_TOKENS)


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def _load_corpus(corpus_key: str) -> tuple[dict[str, Any], ...]:
    if corpus_key != "cgst_section_54":
        return tuple()
    index = _read_json(_GST54_DIR / "index.json")
    rows: list[dict[str, Any]] = []
    for entry in index.get("judgments") or []:
        filename = str(entry.get("file") or "").strip()
        if not filename:
            continue
        payload = _read_json(_GST54_DIR / filename)
        payload["_seed_file"] = f"gst_section_54_judgments/{filename}"
        payload["_index_entry"] = entry
        rows.append(payload)
    return tuple(rows)


def _score_record(query: str, record: dict[str, Any]) -> float:
    q = _normalize(query)
    if not q:
        return 0.0
    score = 0.0
    for token in record.get("match_tokens") or []:
        t = _normalize(str(token))
        if t and t in q:
            score += 2.0 if len(t) > 4 else 1.0
    for tag in record.get("tags") or []:
        t = _normalize(str(tag))
        if t and t in q:
            score += 0.5
    # Prefer family presence for GST §54 package queries.
    if "section 54" in q or "s.54" in q or re.search(r"\bs\s*54\b", q):
        score += 1.0
    if "refund" in q and ("gst" in q or "cgst" in q):
        score += 1.0
    return score


def retrieve_judgments(
    query: str,
    *,
    corpus_key: str = "cgst_section_54",
    limit: int = 3,
    min_score: float = 2.0,
) -> list[dict[str, Any]]:
    """Return ranked curated digests or an empty list (caller must refuse)."""
    scored: list[tuple[float, dict[str, Any]]] = []
    for record in _load_corpus(corpus_key):
        score = _score_record(query, record)
        if score >= min_score:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("year") or 0)))
    return [dict(row) for _, row in scored[: max(1, limit)]]


def format_judgments_block(hits: list[dict[str, Any]], *, wants_cases: bool) -> str:
    if not wants_cases:
        return (
            "**Judgments**\n"
            "- Not searched for this query. Ask for referred cases / judgments if you "
            "need corpus-backed authorities."
        )
    if not hits:
        return (
            "**Judgments**\n"
            "- No matching judgments retrieved from the current corpus for this query. "
            "LegalMitra will not invent case names. Ingest or sync refund/limitation "
            "judgments for this tenant, then retry with an explicit case-search request."
        )
    lines = [
        "**Judgments** (corpus-backed digests — verify against the reported decision)",
    ]
    for hit in hits:
        citation = hit.get("citation") or "citation verify against law report"
        alt = hit.get("alternative_citations") or []
        alt_txt = f"; also {', '.join(str(a) for a in alt[:2])}" if alt else ""
        focus = hit.get("topic_focus") or hit.get("matter_type") or ""
        ratio = hit.get("ratio") or []
        first_ratio = str(ratio[0]) if ratio else str(hit.get("outcome") or "")
        lines.append(
            f"- **{hit.get('title')}** — {citation}{alt_txt} "
            f"({hit.get('court_name') or 'Court'}, {hit.get('doc_date') or hit.get('year')}). "
            f"Topic focus: {focus}. Digest: {first_ratio}"
        )
    lines.append(
        "- Scope note: digests are curated seed summaries, not full judgments. "
        "Limitation-specific holdings appear only when a matching digest exists."
    )
    return "\n".join(lines)


def citations_from_hits(hits: list[dict[str, Any]], *, retrieved_at: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hit in hits:
        snippet_parts = [
            str(hit.get("topic_focus") or ""),
            str((hit.get("ratio") or ["Advisory digest — verify reported decision."])[0]),
        ]
        out.append(
            {
                "title": str(hit.get("title") or "Judgment digest"),
                "source": str(hit.get("source_uri") or hit.get("court_name") or "curated judgment digest"),
                "source_type": "judgment",
                "snippet": " ".join(p for p in snippet_parts if p).strip()[:500],
                "legal_metadata": {
                    "jurisdiction": hit.get("jurisdiction") or "India",
                    "court_name": hit.get("court_name"),
                    "citation": hit.get("citation"),
                    "act": "Central Goods and Services Tax Act, 2017",
                    "section": "54",
                    "case_name": hit.get("title"),
                    "topic_focus": hit.get("topic_focus"),
                    "seed_file": hit.get("_seed_file"),
                },
                "retrieved_at": retrieved_at,
                "source_date": hit.get("doc_date"),
                "staleness_status": "possibly_stale",
            }
        )
    return out
