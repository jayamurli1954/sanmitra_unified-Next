"""Build IEA <-> BSA crosswalk from comparative PDF.

Source (reference-only backend; not edited):
  Bharatiya Sakshya Adhiniyam 2023 compare with Indian Evidence Act. 1872_16052024.pdf
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

PDF = Path(
    r"D:\sanmitra-backend\data\legal_acts\Bharatiya Sakshya Adhiniyam 2023 compare with Indian Evidence Act. 1872_16052024.pdf"
)
ROOT = Path(r"D:\sanmitra_unified-Next")
FULL_OUT = ROOT / "data" / "legal_seed" / "india_bsa_iea_comparative_v1.json"
CROSSWALK = ROOT / "data" / "legal_seed" / "india_criminal_code_crosswalk_v1.json"

# High-frequency pairs often split across multi-line PDF rows
_CURATED_OVERRIDES = [
    {
        "from_section": "27",
        "to_section": "23",
        "subject": "How much of information received from accused may be proved",
        "notes": "IEA 25/26/27 cluster maps into BSA 23; PDF row often omits BSA cell for 27.",
    },
    {
        "from_section": "65B",
        "to_section": "63",
        "subject": "Admissibility of electronic records",
        "notes": "Commonly cited IEA 65B -> BSA 63.",
    },
]

# BSA: 1 / 2(1)(a) / 23 (1) / 39(2)
_BSA_SEC = re.compile(r"^(\d+(?:\s*\([^)]+\))*)$")
# IEA: 1 / 22-A / 45-A / 3, Para 1
_IEA_SEC = re.compile(
    r"^(\d+(?:\s*-\s*[A-Za-z])?(?:\s*,\s*Para\s*\d+)?)$",
    re.IGNORECASE,
)


def _id_token(section: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", str(section)).strip("-").lower()


def _clean(cell: str | None) -> str:
    if cell is None:
        return ""
    return " ".join(str(cell).replace("\u00a0", " ").split())


def _norm_bsa(value: str) -> str | None:
    text = _clean(value).replace(" ", "")
    if not text or text in {"--", "---", "-", "–", "—"}:
        return None
    if _BSA_SEC.match(_clean(value).replace(" ", "")) or re.match(
        r"^\d+(?:\([^)]+\))*$", text
    ):
        return text
    # Allow spaced form 23 (1)
    spaced = _clean(value)
    m = re.match(r"^(\d+(?:\s*\([^)]+\))*)$", spaced)
    return re.sub(r"\s+", "", m.group(1)) if m else None


def _norm_iea(value: str) -> str | None:
    text = _clean(value)
    if not text or text in {"--", "---", "-", "–", "—"}:
        return None
    m = _IEA_SEC.match(text)
    if not m:
        return None
    raw = m.group(1)
    # 22-A -> 22A ; keep Para marker as 3-P1 for uniqueness when present
    raw = re.sub(r"\s*-\s*", "", raw)
    raw = re.sub(r"\s*,\s*Para\s*", "-P", raw, flags=re.IGNORECASE)
    return raw.replace(" ", "")


def _is_header_row(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()
    return (
        "bharatiya" in joined
        or "indian evidence" in joined
        or joined.startswith("section heading")
        or "chapter" in joined and "section" not in cells[0].lower()
    )


def parse_pdf() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()
    with pdfplumber.open(PDF) as pdf:
        for page_i, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables() or []:
                for raw in table:
                    if not raw:
                        continue
                    cells = [_clean(c) for c in raw]
                    if not any(cells) or _is_header_row(cells):
                        continue

                    # Locate BSA section (usually col0) and IEA section (later col)
                    bsa_sec = _norm_bsa(cells[0]) if cells else None
                    bsa_head = cells[1] if len(cells) > 1 else ""

                    iea_sec = None
                    iea_head = ""
                    remarks = ""
                    # Scan remaining cells for IEA section token
                    for idx in range(2, len(cells)):
                        cand = _norm_iea(cells[idx])
                        if cand:
                            iea_sec = cand
                            # heading often next non-empty non-remark cell
                            for j in range(idx + 1, len(cells)):
                                if cells[j] and cells[j].lower() not in {
                                    "modified",
                                    "deleted",
                                    "new",
                                    "new section",
                                }:
                                    # skip if another section
                                    if _norm_iea(cells[j]) or _norm_bsa(cells[j]):
                                        continue
                                    iea_head = cells[j]
                                    break
                            remarks = cells[-1] if cells[-1] else ""
                            break

                    # Deleted IEA-only row: BSA is --
                    if bsa_sec is None and cells and cells[0] in {"--", "---", "-", "–"}:
                        # find IEA
                        for idx, cell in enumerate(cells[1:], start=1):
                            cand = _norm_iea(cell)
                            if cand:
                                iea_sec = cand
                                iea_head = cells[idx + 1] if idx + 1 < len(cells) else ""
                                break
                        if not iea_sec:
                            continue
                        key = (None, iea_sec)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "from_code": "IEA",
                                "from_section": iea_sec,
                                "to_code": "BSA",
                                "to_section": None,
                                "relation": "repealed_or_omitted",
                                "subject": iea_head,
                                "remarks": remarks,
                                "source_page": page_i,
                                "confidence": "medium",
                            }
                        )
                        continue

                    if not bsa_sec:
                        continue

                    if iea_sec is None:
                        # New BSA section with no IEA counterpart
                        key = (bsa_sec, None)
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(
                            {
                                "from_code": "IEA",
                                "from_section": None,
                                "to_code": "BSA",
                                "to_section": bsa_sec,
                                "relation": "new",
                                "subject": bsa_head,
                                "remarks": remarks,
                                "source_page": page_i,
                                "confidence": "medium",
                            }
                        )
                        continue

                    key = (bsa_sec, iea_sec)
                    if key in seen:
                        continue
                    seen.add(key)
                    relation = "renumbered" if bsa_sec != iea_sec else "equivalent"
                    if remarks and "modified" in remarks.lower():
                        relation = "renumbered"
                    rows.append(
                        {
                            "from_code": "IEA",
                            "from_section": iea_sec,
                            "to_code": "BSA",
                            "to_section": bsa_sec,
                            "relation": relation,
                            "subject": bsa_head or iea_head,
                            "remarks": remarks if remarks.lower() in {"modified", "deleted", "new"} else "",
                            "source_page": page_i,
                            "confidence": "medium",
                        }
                    )
    return rows


def apply_overrides(mapped: list[dict]) -> list[dict]:
    by_from = {}
    for r in mapped:
        # Prefer primary section key without forcing overwrite of distinct subsection targets
        key = re.sub(r"-P\d+$", "", r["from_section"])
        # Keep first primary unless override
        if key not in by_from or ("(" not in str(by_from[key].get("to_section")) and "(" in str(r.get("to_section"))):
            # Prefer more specific existing; still index primary
            pass
        by_from.setdefault(key, r)
        by_from[r["from_section"]] = r

    for ov in _CURATED_OVERRIDES:
        by_from[ov["from_section"]] = {
            "from_code": "IEA",
            "from_section": ov["from_section"],
            "to_code": "BSA",
            "to_section": ov["to_section"],
            "relation": "renumbered",
            "subject": ov["subject"],
            "confidence": "high",
            "source": "curated_override",
            "notes": ov["notes"],
            "remarks": "",
        }
    # Deduplicate by (from,to)
    out = []
    seen = set()
    for r in by_from.values():
        key = (r["from_section"], r["to_section"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def merge_into_crosswalk(mapped: list[dict]) -> None:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    keep = [
        m
        for m in data.get("mappings") or []
        if not (
            (m.get("from_code") == "IEA" and m.get("to_code") == "BSA")
            or (m.get("from_code") == "Evidence" and m.get("to_code") == "BSA")
        )
    ]
    iea_bsa = []
    for row in mapped:
        if not row.get("from_section") or not row.get("to_section"):
            continue
        # Skip para-fragment-only uniqueness collisions: keep all including 3-P1
        item = {
            "id": f"iea-{_id_token(row['from_section'])}-bsa-{_id_token(row['to_section'])}",
            "from_code": "IEA",
            "from_section": row["from_section"],
            "to_code": "BSA",
            "to_section": row["to_section"],
            "relation": row["relation"],
            "subject": row.get("subject") or "",
            "confidence": row.get("confidence") or "medium",
            "source": row.get("source") or PDF.name,
        }
        if row.get("remarks"):
            item["notes"] = row["remarks"]
        iea_bsa.append(item)

    data["mappings"] = keep + iea_bsa
    data["version"] = "1.3"
    data["title"] = (
        "LegalMitra criminal-code crosswalk "
        "(IPC/BNS + CrPC/BNSS + IEA/BSA comparative extracts)"
    )
    notes = data.get("notes") or []
    src_note = (
        "IEA↔BSA pairs derived from "
        f"{PDF.name} (machine JSON: india_bsa_iea_comparative_v1.json). "
        "Verify against Bare Acts / NCRB Sankalan before filing."
    )
    if src_note not in notes:
        notes.insert(0, src_note)
    data["notes"] = notes
    data["iea_bsa_source"] = {
        "pdf": PDF.name,
        "derived_json": "india_bsa_iea_comparative_v1.json",
        "pair_count": len(iea_bsa),
    }
    CROSSWALK.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"crosswalk updated: iea_bsa={len(iea_bsa)} total_mappings={len(data['mappings'])}")


def main() -> None:
    rows = parse_pdf()
    mapped = [r for r in rows if r.get("relation") not in {"new", "repealed_or_omitted"}]
    mapped = apply_overrides(mapped)
    newish = [r for r in rows if r.get("relation") == "new"]
    omitted = [r for r in rows if r.get("relation") == "repealed_or_omitted"]

    payload = {
        "version": "1.0",
        "title": "BSA ↔ Indian Evidence Act Corresponding Section Table (machine extract)",
        "source_pdf": PDF.name,
        "source_note": (
            "Extracted for LegalMitra deterministic lookup. Confirm against Bare Acts / "
            "NCRB Sankalan before filing. Human review required."
        ),
        "counts": {
            "total_rows": len(rows),
            "mapped": len(mapped),
            "new": len(newish),
            "repealed_or_omitted": len(omitted),
        },
        "rows": rows,
    }
    FULL_OUT.parent.mkdir(parents=True, exist_ok=True)
    FULL_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {FULL_OUT} counts={payload['counts']}")
    merge_into_crosswalk(mapped)

    checks = {
        ("65B", "63"): False,  # electronic records often cited — may or may not exist
        ("25", "23"): False,  # confession to police
        ("45", "39"): False,  # expert opinion parent
        ("3", "2"): False,  # definitions
        ("5", "3"): False,  # relevancy
    }
    for r in mapped:
        # strip para suffixes for loose check
        fr = re.sub(r"-P\d+$", "", r["from_section"])
        to = r["to_section"]
        for want_fr, want_to in list(checks.keys()):
            if fr == want_fr and (to == want_to or to.startswith(want_to + "(")):
                checks[(want_fr, want_to)] = True
    print("spot_checks", checks)
    # Print a few sample high-frequency
    for sec in ("25", "65B", "45", "27"):
        hits = [r for r in mapped if re.sub(r"-P\d+$", "", r["from_section"]) == sec]
        print(sec, [(h["to_section"], h["subject"][:50]) for h in hits[:3]])


if __name__ == "__main__":
    main()
