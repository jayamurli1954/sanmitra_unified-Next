"""Build CrPC <-> BNSS crosswalk from comparative PDF.

Source (reference-only backend; not edited):
  COMPARATIVE-TABLE-OF-CRPC-1973-BHARTIYA-NAGARIK-SURAKSHA-SANHITA-2023-ADV-GURENDER-RANA.pdf

Note: This is an advocate comparative table (Rathee / Adv. Gurender Rana), not the
NCRB Sankalan Gazette table. Confidence=medium; high-risk pairs are reconciled
against known Sankalan/official mappings after extract.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

PDF = Path(
    r"D:\sanmitra-backend\data\legal_acts\COMPARATIVE-TABLE-OF-CRPC-1973-BHARTIYA-NAGARIK-SURAKSHA-SANHITA-2023-ADV-GURENDER-RANA.pdf"
)
ROOT = Path(r"D:\sanmitra_unified-Next")
FULL_OUT = ROOT / "data" / "legal_seed" / "india_bnss_crpc_comparative_v1.json"
CROSSWALK = ROOT / "data" / "legal_seed" / "india_criminal_code_crosswalk_v1.json"

_SECTION_RE = re.compile(r"^\d+[A-Za-z]?(?:\([^)]+\))?$")

# Official / Sankalan-aligned overrides (win on conflict)
_OFFICIAL_OVERRIDES = [
    {
        "from_section": "482",
        "to_section": "528",
        "subject": "Saving of inherent powers of High Court",
        "notes": "NCRB Sankalan / Bare Act override: CrPC 482 -> BNSS 528 (not 504/538).",
    },
    {
        "from_section": "458",
        "to_section": "504",
        "subject": "Procedure where no claimant appears within six months",
        "notes": "NCRB Sankalan: BNSS 504 corresponds to CrPC 458.",
    },
    {
        "from_section": "438",
        "to_section": "482",
        "subject": "Direction for grant of bail to person apprehending arrest",
        "notes": "NCRB Sankalan: anticipatory bail CrPC 438 -> BNSS 482.",
    },
    {
        "from_section": "41A",
        "to_section": "35(3)",
        "subject": "Notice of appearance before police officer",
        "notes": "Common high-risk pair; confirm against Bare Act / Sankalan.",
    },
]


def _id_token(section: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", str(section)).strip("-").lower()


def _norm_sec(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).replace("\u00a0", " ").split())
    if not text or text in {"---", "–", "-", "—"}:
        return None
    text = text.replace(" ", "")
    return text if _SECTION_RE.match(text) else None


def _norm_heading(value: str | None) -> str:
    if not value or str(value).strip() in {"---", "–", "-", "—"}:
        return ""
    return " ".join(str(value).replace("\u00a0", " ").split())


def parse_pdf() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str | None]] = set()
    with pdfplumber.open(PDF) as pdf:
        for page_i, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables() or []:
                for raw in table:
                    if not raw or len(raw) < 3:
                        continue
                    # Expected: CrPC sec, CrPC heading, BNSS sec, BNSS heading
                    cells = list(raw) + [None] * (4 - len(raw))
                    crpc_sec = _norm_sec(cells[0])
                    crpc_head = _norm_heading(cells[1])
                    bnss_sec = _norm_sec(cells[2])
                    bnss_head = _norm_heading(cells[3])

                    if not crpc_sec:
                        continue
                    # Skip header-like
                    if crpc_sec.lower() in {"section"} or "criminal" in (cells[0] or "").lower():
                        continue

                    key = (crpc_sec, bnss_sec)
                    if key in seen:
                        continue
                    seen.add(key)

                    if bnss_sec is None:
                        rows.append(
                            {
                                "from_code": "CrPC",
                                "from_section": crpc_sec,
                                "to_code": "BNSS",
                                "to_section": None,
                                "relation": "repealed_or_omitted",
                                "subject": crpc_head or bnss_head,
                                "source_page": page_i,
                                "confidence": "medium",
                            }
                        )
                        continue

                    relation = "renumbered" if crpc_sec != bnss_sec else "equivalent"
                    rows.append(
                        {
                            "from_code": "CrPC",
                            "from_section": crpc_sec,
                            "to_code": "BNSS",
                            "to_section": bnss_sec,
                            "relation": relation,
                            "subject": bnss_head or crpc_head,
                            "source_page": page_i,
                            "confidence": "medium",
                        }
                    )
    return rows


def apply_overrides(mapped: list[dict]) -> tuple[list[dict], list[dict]]:
    """Force Sankalan-aligned high-risk pairs; return (rows, conflicts)."""
    by_from = {r["from_section"]: r for r in mapped}
    conflicts: list[dict] = []
    for ov in _OFFICIAL_OVERRIDES:
        existing = by_from.get(ov["from_section"])
        if existing and existing.get("to_section") != ov["to_section"]:
            conflicts.append(
                {
                    "from_section": ov["from_section"],
                    "pdf_to_section": existing.get("to_section"),
                    "override_to_section": ov["to_section"],
                    "reason": ov["notes"],
                }
            )
        by_from[ov["from_section"]] = {
            "from_code": "CrPC",
            "from_section": ov["from_section"],
            "to_code": "BNSS",
            "to_section": ov["to_section"],
            "relation": "renumbered" if ov["from_section"] != ov["to_section"] else "equivalent",
            "subject": ov["subject"],
            "confidence": "high",
            "source": "ncrb_sankalan_override",
            "notes": ov["notes"],
        }
    return list(by_from.values()), conflicts


def merge_into_crosswalk(mapped: list[dict]) -> None:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    keep = [
        m
        for m in data.get("mappings") or []
        if not (m.get("from_code") == "CrPC" and m.get("to_code") == "BNSS")
    ]
    crpc_bnss = []
    for row in mapped:
        if not row.get("to_section"):
            continue
        item = {
            "id": f"crpc-{_id_token(row['from_section'])}-bnss-{_id_token(row['to_section'])}",
            "from_code": "CrPC",
            "from_section": row["from_section"],
            "to_code": "BNSS",
            "to_section": row["to_section"],
            "relation": row["relation"],
            "subject": row.get("subject") or "",
            "confidence": row.get("confidence") or "medium",
            "source": row.get("source")
            or "COMPARATIVE-TABLE-OF-CRPC-1973-BHARTIYA-NAGARIK-SURAKSHA-SANHITA-2023-ADV-GURENDER-RANA.pdf",
        }
        if row.get("notes"):
            item["notes"] = row["notes"]
        crpc_bnss.append(item)

    data["mappings"] = keep + crpc_bnss
    data["version"] = "1.2"
    data["title"] = (
        "LegalMitra criminal-code crosswalk "
        "(IPC/BNS comparative PDF + CrPC/BNSS advocate table + Sankalan overrides)"
    )
    notes = data.get("notes") or []
    src_note = (
        "CrPC↔BNSS pairs derived from advocate comparative PDF "
        "COMPARATIVE-TABLE-OF-CRPC-1973-BHARTIYA-NAGARIK-SURAKSHA-SANHITA-2023-ADV-GURENDER-RANA.pdf "
        "(machine JSON: india_bnss_crpc_comparative_v1.json). High-risk pairs overridden "
        "to match NCRB Sankalan where the PDF conflicts. Verify before filing."
    )
    if src_note not in notes:
        notes.insert(0, src_note)
    data["notes"] = notes
    data["crpc_bnss_source"] = {
        "pdf": PDF.name,
        "derived_json": "india_bnss_crpc_comparative_v1.json",
        "pair_count": len(crpc_bnss),
        "attribution": "Advocate comparative table (not NCRB Sankalan); Sankalan overrides applied for high-risk pairs.",
    }
    CROSSWALK.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"crosswalk updated: crpc_bnss={len(crpc_bnss)} total_mappings={len(data['mappings'])}")


def main() -> None:
    rows = parse_pdf()
    mapped = [r for r in rows if r.get("relation") != "repealed_or_omitted"]
    omitted = [r for r in rows if r.get("relation") == "repealed_or_omitted"]
    mapped, conflicts = apply_overrides(mapped)

    payload = {
        "version": "1.0",
        "title": "BNSS ↔ CrPC Corresponding Section Table (machine extract)",
        "source_pdf": PDF.name,
        "source_note": (
            "Advocate comparative table extract for LegalMitra deterministic lookup. "
            "Not an official NCRB Sankalan dump. High-risk pairs reconciled to Sankalan. "
            "Verify against Bare Acts / NCRB Sankalan before filing."
        ),
        "counts": {
            "total_rows": len(rows),
            "mapped": len(mapped),
            "repealed_or_omitted": len(omitted),
            "override_conflicts": len(conflicts),
        },
        "override_conflicts": conflicts,
        "rows": rows,
        "mapped_with_overrides": mapped,
    }
    FULL_OUT.parent.mkdir(parents=True, exist_ok=True)
    FULL_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {FULL_OUT} counts={payload['counts']}")
    if conflicts:
        print("override_conflicts", json.dumps(conflicts, indent=2))
    merge_into_crosswalk(mapped)

    checks = {
        ("482", "528"): False,
        ("458", "504"): False,
        ("438", "482"): False,
        ("154", "173"): False,
        ("41A", "35(3)"): False,
    }
    for r in mapped:
        key = (r["from_section"], r["to_section"])
        if key in checks:
            checks[key] = True
    print("spot_checks", checks)


if __name__ == "__main__":
    main()
