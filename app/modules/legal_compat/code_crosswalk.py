"""Curated IPC/CrPC <-> BNS/BNSS crosswalk lookup (anti-hallucination tool).

v1 is a curated seed of high-frequency / high-confusion pairs — not a claim of
complete Gazette coverage. Always verify against Bare Acts before filing.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_DATA_PATH = _ROOT / "data" / "legal_seed" / "india_criminal_code_crosswalk_v1.json"

_CODE_ALIASES = {
    "ipc": "IPC",
    "indian penal code": "IPC",
    "bns": "BNS",
    "bharatiya nyaya sanhita": "BNS",
    "crpc": "CrPC",
    "cr.p.c": "CrPC",
    "cr.p.c.": "CrPC",
    "code of criminal procedure": "CrPC",
    "bnss": "BNSS",
    "bharatiya nagarik suraksha sanhita": "BNSS",
    "iea": "IEA",
    "evidence act": "IEA",
    "bsa": "BSA",
    "bharatiya sakshya adhiniyam": "BSA",
}

_SECTION_RE = re.compile(r"^\d+[A-Z]?(?:\(\d+\))?$")


def normalize_code(code: str | None) -> str | None:
    raw = " ".join((code or "").strip().lower().replace("_", " ").split())
    if not raw:
        return None
    if raw in _CODE_ALIASES:
        return _CODE_ALIASES[raw]
    # Preserve CrPC-style mixed case when already canonical-ish
    upper = raw.upper()
    if upper in {"IPC", "BNS", "CRPC", "BNSS", "IEA", "BSA"}:
        return "CrPC" if upper == "CRPC" else upper
    if "evidence" in raw:
        return "IEA"
    if "sakshya" in raw:
        return "BSA"
    return None


def normalize_section(section: str | None) -> str | None:
    raw = (section or "").strip().upper().replace(" ", "")
    raw = re.sub(r"^(SECTION|SEC\.?|S\.?)", "", raw, flags=re.IGNORECASE)
    raw = raw.strip(" .")
    if not raw:
        return None
    return raw if _SECTION_RE.match(raw) else raw


def sections_compatible(a: str | None, b: str | None) -> bool:
    """True if exact match or parent/subsection (318 vs 318(4))."""
    left = normalize_section(a)
    right = normalize_section(b)
    if not left or not right:
        return False
    if left == right:
        return True
    return left.startswith(right + "(") or right.startswith(left + "(")


@lru_cache(maxsize=1)
def load_crosswalk() -> dict[str, Any]:
    if not _DATA_PATH.exists():
        return {"version": "missing", "mappings": [], "known_false_mappings": [], "notes": []}
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def list_mappings(
    *,
    from_code: str | None = None,
    to_code: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    data = load_crosswalk()
    fc = normalize_code(from_code) if from_code else None
    tc = normalize_code(to_code) if to_code else None
    out: list[dict[str, Any]] = []
    for row in data.get("mappings") or []:
        if fc and str(row.get("from_code")) != fc:
            continue
        if tc and str(row.get("to_code")) != tc:
            continue
        out.append(dict(row))
        if len(out) >= limit:
            break
    return out


def lookup(
    *,
    from_code: str,
    section: str,
    direction: str = "forward",
) -> dict[str, Any]:
    """Lookup one section.

    direction=forward: legacy -> new (IPC/CrPC -> BNS/BNSS)
    direction=reverse: new -> legacy
    """
    code = normalize_code(from_code)
    sec = normalize_section(section)
    if not code or not sec:
        return {
            "found": False,
            "query": {"from_code": from_code, "section": section, "direction": direction},
            "matches": [],
            "note": "code and section are required",
            "human_review_required": True,
        }

    data = load_crosswalk()
    matches: list[dict[str, Any]] = []
    forward = (direction or "forward").lower() != "reverse"

    for row in data.get("mappings") or []:
        if forward:
            if str(row.get("from_code")) == code and normalize_section(str(row.get("from_section"))) == sec:
                matches.append(dict(row))
        else:
            if str(row.get("to_code")) == code and normalize_section(str(row.get("to_section"))) == sec:
                matches.append(dict(row))

    return {
        "found": bool(matches),
        "query": {"from_code": code, "section": sec, "direction": "forward" if forward else "reverse"},
        "matches": matches,
        "registry_version": data.get("version"),
        "advisory": (
            "Curated LegalMitra seed crosswalk. Confirm against Bare Acts / India Code before filing."
        ),
        "human_review_required": True,
        "not_found_policy": (
            None
            if matches
            else "Mapping not in curated seed. Do not invent a successor section; verify against Bare Acts."
        ),
    }


def detect_false_mapping(
    *,
    from_code: str,
    from_section: str,
    to_code: str,
    to_section: str,
) -> dict[str, Any] | None:
    """Return a known-false mapping record if this pair is a documented hallucination."""
    fc = normalize_code(from_code)
    fs = normalize_section(from_section)
    tc = normalize_code(to_code)
    ts = normalize_section(to_section)
    if not all([fc, fs, tc, ts]):
        return None
    for row in load_crosswalk().get("known_false_mappings") or []:
        if (
            str(row.get("claimed_from_code")) == fc
            and normalize_section(str(row.get("claimed_from_section"))) == fs
            and str(row.get("claimed_to_code")) == tc
            and normalize_section(str(row.get("claimed_to_section"))) == ts
        ):
            return dict(row)
    return None


def prompt_crosswalk_snippet(max_rows: int = 12) -> str:
    """Compact prompt appendix for senior-counsel generation."""
    rows = list_mappings(limit=max_rows)
    lines = [
        "CURATED CODE CROSSWALK (verify; high-frequency pairs only):",
        "- CrPC 482 -> BNSS 528 (inherent powers). NOT BNSS 504/538.",
        "- IPC 504 -> BNS 352 (insult). BNSS 504 is a different seized-property procedure.",
    ]
    for row in rows[:max_rows]:
        lines.append(
            f"- {row.get('from_code')} {row.get('from_section')} -> "
            f"{row.get('to_code')} {row.get('to_section')} ({row.get('subject') or row.get('relation')})"
        )
    lines.append("If a mapping is missing from this list, say verification is required; do not invent.")
    return "\n".join(lines)
