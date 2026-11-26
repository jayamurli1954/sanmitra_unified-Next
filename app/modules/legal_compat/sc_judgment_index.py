"""Supreme Court judgment index (metadata only) with on-demand PDF links.

Built by ``scripts/build_sc_judgment_index.py`` from "Indian Supreme Court
Judgments" (Dattam Labs, AWS Open Data Registry, CC BY 4.0). ~38k judgments,
1950 onwards: party names, decision date, neutral citation (e.g. "2021 INSC
469") and SCR citation. PDFs are not stored; ``pdf_url`` points at the public
bucket so a judgment is opened / fetched only when someone needs it.

The data does not include SCC / AIR citations (those reporters are proprietary),
so a case cited by SCC can be identified by name and year but its SCC page
number cannot be checked.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.modules.legal_compat.case_citation_audit import _GENERIC_TOKENS

_ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = _ROOT / "data" / "legal_seed" / "sc_judgment_index"
INDEX_FILE = INDEX_DIR / "sc_judgments.jsonl.gz"
MANIFEST_FILE = INDEX_DIR / "manifest.json"

BUCKET_URL = "https://indian-supreme-court-judgments.s3.amazonaws.com"
ATTRIBUTION = (
    "Supreme Court judgment data: Dattam Labs, Indian Supreme Court Judgments "
    "(AWS Open Data Registry), CC BY 4.0"
)

_SEP_RE = re.compile(r"\s+(?:v\.?|vs\.?|versus|V/s\.?)\s+", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace(".", " "))


def _distinctive(text: str) -> list[str]:
    out: list[str] = []
    for tok in _tokens(text):
        if tok in _GENERIC_TOKENS or len(tok) < 2 or tok.isdigit() or tok in out:
            continue
        out.append(tok)
    return out


def _with_joins(tokens: list[str]) -> set[str]:
    out = set(tokens)
    out.update(_join_pairs(tokens))
    return out


def citation_key(text: str) -> tuple[str, ...]:
    """Normalise SCR / neutral citations: "[2021] 15 S.C.R. 169" -> ("2021","15","scr","169")."""
    flat = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", "", text or "").replace(".", " ")
    return tuple(re.findall(r"[a-z]+|\d+", flat.lower()))


def is_held_reporter(citation: str) -> bool:
    """True for citation kinds this index holds (SCR and neutral INSC)."""
    key = citation_key(citation)
    return "scr" in key or "insc" in key


def citation_year(citation: str | None) -> int | None:
    m = _YEAR_RE.search(citation or "")
    return int(m.group(1)) if m else None


# Compact row: a tuple in this field order. The title is "<p> versus <r>" in the
# source data, so it is only stored when it differs from that.
_FIELDS = ("p", "r", "t", "nc", "scr", "d", "y", "j", "dn", "path")


def _pack(row: dict[str, Any]) -> tuple:
    p, r, t = row.get("p") or "", row.get("r") or "", row.get("t") or ""
    if t == f"{p} versus {r}":
        t = ""
    if not p and not r:
        p, _, r = t.partition(" versus ")
        t = ""
    intern = sys.intern
    return (
        p, r, t, row.get("nc") or "", row.get("scr") or "", row.get("d") or "",
        int(row.get("y") or 0), row.get("j") or "", intern(row.get("dn") or ""), row.get("path") or "",
    )


def _unpack(packed: tuple) -> dict[str, Any]:
    row = {k: v for k, v in zip(_FIELDS, packed) if v not in ("", 0)}
    if not row.get("t"):
        row["t"] = f"{packed[0]} versus {packed[1]}"
    return row


def _join_pairs(tokens: list[str]) -> set[str]:
    """Joins of short adjacent tokens, so "GOLAK NATH" also matches "Golaknath"."""
    return {a + b for a, b in zip(tokens, tokens[1:]) if len(a) <= 6 and len(b) <= 6 and not (a + b).isdigit()}


class SupremeCourtIndex:
    """In-memory index. Kept lean: postings are int arrays, side tokens are
    computed only for the handful of candidates a query touches."""

    def __init__(self, rows: Iterable[dict[str, Any]]) -> None:
        from array import array

        self._rows: list[tuple] = []
        self._by_citation: dict[str, int] = {}
        postings: dict[str, array] = {}
        for i, row in enumerate(rows):
            packed = _pack(row)
            self._rows.append(packed)
            for value in (packed[3], packed[4]):
                if value:
                    self._by_citation.setdefault(" ".join(citation_key(value)), i)
            pet, res = packed[0], packed[1]
            for tok in _with_joins(_tokens(pet)) | _with_joins(_tokens(res)):
                if tok in _GENERIC_TOKENS or len(tok) < 2 or tok.isdigit():
                    continue
                bucket = postings.get(tok)
                if bucket is None:
                    bucket = postings[tok] = array("i")
                bucket.append(i)
        self._postings = postings

    def _side_tokens(self, i: int) -> tuple[set[str], set[str]]:
        packed = self._rows[i]
        return _with_joins(_tokens(packed[0])), _with_joins(_tokens(packed[1]))

    def row(self, i: int) -> dict[str, Any]:
        return _unpack(self._rows[i])

    def __len__(self) -> int:
        return len(self._rows)

    # ── lookups ───────────────────────────────────────────────────────────

    def by_citation(self, citation: str) -> dict[str, Any] | None:
        idx = self._by_citation.get(" ".join(citation_key(citation)))
        return self.row(idx) if idx is not None else None

    @staticmethod
    def _side_ok(claim_side: list[str], record_side: set[str]) -> bool:
        if not claim_side:
            return True
        hits = sum(1 for t in claim_side if t in record_side)
        return hits >= max(1, -(-len(claim_side) * 2 // 3))

    @staticmethod
    def _side_terms(text: str) -> list[str]:
        """Distinctive tokens; for an all-generic party ("Union of India") its generic words."""
        distinct = _distinctive(text)
        if distinct:
            return distinct
        return [t for t in _tokens(text) if t not in {"of", "the", "and", "ors", "anr", "others", "another"}]

    def name_matches(self, name: str, row: dict[str, Any]) -> bool:
        """Does a cited case name fit this record's parties (either order)?"""
        parts = _SEP_RE.split(name or "", maxsplit=1)
        left = self._side_terms(parts[0])
        right = self._side_terms(parts[1]) if len(parts) > 1 else []
        if not _distinctive(name or ""):
            return False
        pet = _with_joins(_tokens(row.get("p") or ""))
        res = _with_joins(_tokens(row.get("r") or ""))
        return (self._side_ok(left, pet) and self._side_ok(right, res)) or (
            self._side_ok(left, res) and self._side_ok(right, pet)
        )

    def by_name(self, name: str, *, year: int | None = None, limit: int = 5) -> list[dict[str, Any]]:
        parts = _SEP_RE.split(name or "", maxsplit=1)
        left = self._side_terms(parts[0])
        right = self._side_terms(parts[1]) if len(parts) > 1 else []
        distinctive = _distinctive(name or "")
        if not distinctive:
            return []
        # Candidate set from the rarest distinctive token present in the index.
        present = [t for t in distinctive if t in self._postings]
        if not present:
            return []
        rarest = min(present, key=lambda t: len(self._postings[t]))
        matches: list[int] = []
        for i in self._postings[rarest]:
            pet, res = self._side_tokens(i)
            if (self._side_ok(left, pet) and self._side_ok(right, res)) or (
                self._side_ok(left, res) and self._side_ok(right, pet)
            ):
                matches.append(i)
        if year is not None:
            near = [i for i in matches if abs(int(self._rows[i][6] or 0) - year) <= 1]
            if near:
                matches = near
        return [self.row(i) for i in matches[:limit]]

    def search(self, query: str, *, year: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Free-text party / citation search for the Judgment Finder."""
        query = (query or "").strip()
        if not query:
            return []
        hit = self.by_citation(query)
        if hit:
            return [hit]
        if _SEP_RE.search(query):
            return self.by_name(query, year=year, limit=limit)
        tokens = [t for t in _distinctive(query) if t in self._postings]
        if not tokens:
            return []
        candidate_ids = set(self._postings[min(tokens, key=lambda t: len(self._postings[t]))])
        for tok in tokens:
            candidate_ids &= set(self._postings[tok])
        rows = [self.row(i) for i in sorted(candidate_ids)]
        if year is not None:
            rows = [r for r in rows if abs(int(r.get("y") or 0) - year) <= 1] or rows
        rows.sort(key=lambda r: r.get("d") or "", reverse=True)
        return rows[:limit]


def pdf_url(row: dict[str, Any]) -> str | None:
    path, year = row.get("path"), row.get("y")
    if not path or not year:
        return None
    return f"{BUCKET_URL}/data/pdf/year={year}/english/{path}_EN.pdf"


def public_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": row.get("t"),
        "petitioner": row.get("p"),
        "respondent": row.get("r"),
        "neutral_citation": row.get("nc"),
        "scr_citation": row.get("scr"),
        "decision_date": row.get("d"),
        "year": row.get("y"),
        "bench": row.get("j"),
        "disposal": row.get("dn"),
        "court": "Supreme Court of India",
        "pdf_url": pdf_url(row),
        "source": "sc_open_data_index",
    }


@lru_cache(maxsize=1)
def get_index() -> SupremeCourtIndex:
    """Load lazily on first use; an absent file yields an empty index."""
    def _rows():
        if INDEX_FILE.exists():
            with gzip.open(INDEX_FILE, "rt", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)

    return SupremeCourtIndex(_rows())
