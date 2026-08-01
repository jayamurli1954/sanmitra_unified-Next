"""Build machine-readable IPC <-> BNS crosswalk from comparative PDF.

Source (reference-only backend; not edited):
  D:\\sanmitra-backend\\data\\legal_acts\\202406281710564823BNS_IPC_Comparative.pdf

Writes into sanmitra_unified-Next:
  data/legal_seed/india_bns_ipc_comparative_v1.json
  and merges into india_criminal_code_crosswalk_v1.json (IPC/BNS rows).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

PDF = Path(r"D:\sanmitra-backend\data\legal_acts\202406281710564823BNS_IPC_Comparative.pdf")
ROOT = Path(r"D:\sanmitra_unified-Next")
FULL_OUT = ROOT / "data" / "legal_seed" / "india_bns_ipc_comparative_v1.json"
CROSSWALK = ROOT / "data" / "legal_seed" / "india_criminal_code_crosswalk_v1.json"


def _id_token(section: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", str(section)).strip("-").lower()


# Leading section token: 64 / 65(1) / 120B / 376AB / 318 (4) / 8(6)(a)
_SECTION_HEAD = re.compile(
    r"^\s*(Deleted\s+)?(?P<section>\d+[A-Za-z]?(?:\s*\([^)]+\))*)(?=\s|$|\.)",
    re.IGNORECASE,
)
_SKIP_RIGHT = {
    "new section",
    "new sub-section",
    "new sub section",
}
_HEADER_HINTS = ("chapter", "bharatiya", "indian penal", "of offences", "of abetment")


def _clean(cell: str | None) -> str:
    if not cell:
        return ""
    return " ".join(str(cell).replace("\u00a0", " ").split())


def _extract_section(cell: str) -> tuple[str | None, str, bool]:
    """Return (section, subject_rest, is_deleted_marker)."""
    text = _clean(cell)
    if not text:
        return None, "", False
    lower = text.lower()
    if any(h in lower for h in _HEADER_HINTS) and not _SECTION_HEAD.match(text):
        return None, text, False
    m = _SECTION_HEAD.match(text)
    if not m:
        return None, text, False
    deleted = bool(m.group(1))
    section = re.sub(r"\s+", "", m.group("section"))
    rest = text[m.end() :].lstrip(" .:-–—").strip()
    return section, rest, deleted


def _is_new_marker(text: str) -> bool:
    return _clean(text).lower() in _SKIP_RIGHT or _clean(text).lower().startswith("new ")


def parse_pdf() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    with pdfplumber.open(PDF) as pdf:
        for page_i, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for table in tables:
                for raw in table:
                    if not raw or len(raw) < 2:
                        continue
                    left = _clean(raw[0])
                    right = _clean(raw[1])
                    if not left and not right:
                        continue
                    # Skip repeated column headers
                    if "bharatiya" in left.lower() or "2023 (bns)" in left.lower():
                        continue
                    if "indian penal" in right.lower() or "1860 (ipc)" in right.lower():
                        continue

                    bns_sec, bns_subj, bns_deleted = _extract_section(left)
                    ipc_sec, ipc_subj, ipc_deleted = _extract_section(right)

                    # Pure "Deleted" left cell with IPC on right = repealed IPC
                    if left.lower().startswith("deleted") and ipc_sec:
                        key = ("", ipc_sec)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "from_code": "IPC",
                                "from_section": ipc_sec,
                                "to_code": "BNS",
                                "to_section": None,
                                "relation": "repealed",
                                "subject": ipc_subj or bns_subj,
                                "source_page": page_i,
                                "confidence": "high",
                            }
                        )
                        continue

                    if not bns_sec:
                        continue

                    if _is_new_marker(right) or (not ipc_sec and "new" in right.lower()):
                        key = (bns_sec, "")
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "from_code": "IPC",
                                "from_section": None,
                                "to_code": "BNS",
                                "to_section": bns_sec,
                                "relation": "new",
                                "subject": bns_subj,
                                "source_page": page_i,
                                "confidence": "high",
                            }
                        )
                        continue

                    if not ipc_sec:
                        continue

                    key = (bns_sec, ipc_sec)
                    if key in seen:
                        continue
                    seen.add(key)
                    subject = bns_subj or ipc_subj
                    relation = "renumbered" if bns_sec != ipc_sec else "equivalent"
                    # Many renumbered still equivalent in substance; mark renumbered when numbers differ
                    rows.append(
                        {
                            "from_code": "IPC",
                            "from_section": ipc_sec,
                            "to_code": "BNS",
                            "to_section": bns_sec,
                            "relation": relation,
                            "subject": subject.lstrip("."),
                            "source_page": page_i,
                            "confidence": "high",
                        }
                    )
    return rows


def merge_into_crosswalk(comparative: list[dict]) -> None:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    # Keep non-IPC/BNS mappings and known_false; replace IPC->BNS from comparative.
    keep = [
        m
        for m in data.get("mappings") or []
        if not (m.get("from_code") == "IPC" and m.get("to_code") == "BNS")
        and not (m.get("from_code") == "CrPC" and m.get("to_code") == "BNS")
    ]
    # Prefer substantive offence mappings (skip pure definitional 2(x) noise optionally —
    # include all for anti-hallucination completeness)
    ipc_bns = []
    for row in comparative:
        if row.get("relation") in {"new", "repealed"}:
            continue
        if not row.get("from_section") or not row.get("to_section"):
            continue
        ipc_bns.append(
            {
                "id": (
                    f"ipc-{_id_token(row['from_section'])}-bns-{_id_token(row['to_section'])}"
                ),
                "from_code": "IPC",
                "from_section": row["from_section"],
                "to_code": "BNS",
                "to_section": row["to_section"],
                "relation": row["relation"],
                "subject": row.get("subject") or "",
                "confidence": "high",
                "source": "BNS_IPC_Comparative.pdf",
            }
        )

    # Deduplicate by from_section preferring longer/more specific to_section? Keep first
    # occurrence but if multiple IPC sections map, keep all; if same IPC maps to multiple BNS, keep all.
    data["mappings"] = keep + ipc_bns
    data["version"] = "1.1"
    data["title"] = "LegalMitra criminal-code crosswalk (IPC/BNS from comparative PDF + curated CrPC/BNSS)"
    notes = data.get("notes") or []
    src_note = (
        "IPC↔BNS pairs derived from Corresponding Section Table PDF "
        "202406281710564823BNS_IPC_Comparative.pdf (reference copy under "
        "sanmitra-backend/data/legal_acts/; machine JSON in india_bns_ipc_comparative_v1.json)."
    )
    if src_note not in notes:
        notes.insert(0, src_note)
    data["notes"] = notes
    data["ipc_bns_source"] = {
        "pdf": "202406281710564823BNS_IPC_Comparative.pdf",
        "derived_json": "india_bns_ipc_comparative_v1.json",
        "pair_count": len(ipc_bns),
    }
    CROSSWALK.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"crosswalk updated: ipc_bns={len(ipc_bns)} total_mappings={len(data['mappings'])}")


def main() -> None:
    rows = parse_pdf()
    mapped = [r for r in rows if r.get("relation") not in {"new", "repealed"}]
    newish = [r for r in rows if r.get("relation") == "new"]
    repealed = [r for r in rows if r.get("relation") == "repealed"]
    payload = {
        "version": "1.0",
        "title": "BNS ↔ IPC Corresponding Section Table (machine extract)",
        "source_pdf": str(PDF.name),
        "source_note": (
            "Extracted for LegalMitra deterministic lookup. Verify against Bare Acts / "
            "NCRB Sankalan before filing. Not a substitute for human review."
        ),
        "counts": {
            "total_rows": len(rows),
            "mapped": len(mapped),
            "new": len(newish),
            "repealed": len(repealed),
        },
        "rows": rows,
    }
    FULL_OUT.parent.mkdir(parents=True, exist_ok=True)
    FULL_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {FULL_OUT} counts={payload['counts']}")
    merge_into_crosswalk(rows)

    # Spot-check high-risk pairs
    checks = {
        ("420", "318"): False,
        ("302", "103"): False,
        ("504", "352"): False,
        ("376", "64"): False,
        ("120B", "61(2)"): False,
        ("34", "3(5)"): False,
    }
    for r in mapped:
        key = (r["from_section"], r["to_section"])
        # also accept 318(4) for 420
        if r["from_section"] == "420" and str(r["to_section"]).startswith("318"):
            checks[("420", "318")] = True
        if key in checks:
            checks[key] = True
        if r["from_section"] == "120B" and str(r["to_section"]).startswith("61"):
            checks[("120B", "61(2)")] = True
    print("spot_checks", checks)


if __name__ == "__main__":
    main()
