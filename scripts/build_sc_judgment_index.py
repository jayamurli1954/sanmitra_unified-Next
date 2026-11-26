"""Build LegalMitra's Supreme Court judgment index from the public AWS Open Data set.

Source: "Indian Supreme Court Judgments" by Dattam Labs, AWS Open Data Registry
(https://registry.opendata.aws/indian-supreme-court-judgments/), CC BY 4.0.

Downloads the per-year ``metadata.parquet`` files (no AWS account needed — the
bucket is public), keeps only the fields LegalMitra needs, and writes a compact
gzip JSON-lines index. Judgment PDFs are NOT downloaded; they are linked and
fetched on demand from the public bucket.

Usage (needs pyarrow: ``pip install pyarrow``):
  python scripts/build_sc_judgment_index.py
  python scripts/build_sc_judgment_index.py --from-year 2015 --to-year 2025
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "legal_seed" / "sc_judgment_index"
OUT_FILE = OUT_DIR / "sc_judgments.jsonl.gz"
MANIFEST = OUT_DIR / "manifest.json"
BUCKET_URL = "https://indian-supreme-court-judgments.s3.amazonaws.com"


def _fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "legal-index-builder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            return None
        raise


def _clean(value) -> str:
    text = " ".join(str(value or "").split())
    return "" if text.lower() in {"none", "nan", "null"} else text


def _iso_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%d-%m-%Y").date().isoformat()
    except ValueError:
        return ""


def _rows_for_year(year: int) -> list[dict]:
    import pyarrow.parquet as pq

    payload = _fetch(f"{BUCKET_URL}/metadata/parquet/year={year}/metadata.parquet")
    if payload is None:
        return []
    columns = [
        "title", "petitioner", "respondent", "judge", "citation", "case_id",
        "decision_date", "disposal_nature", "path", "year", "available_languages",
    ]
    table = pq.read_table(io.BytesIO(payload))
    present = [c for c in columns if c in table.column_names]
    out: list[dict] = []
    for raw in table.select(present).to_pylist():
        path = _clean(raw.get("path"))
        if not path:
            continue
        row = {
            "t": _clean(raw.get("title")),
            "p": _clean(raw.get("petitioner")),
            "r": _clean(raw.get("respondent")),
            "nc": _clean(raw.get("case_id")),       # neutral citation, e.g. "2021 INSC 306"
            "scr": _clean(raw.get("citation")),     # e.g. "[2021] 6 S.C.R. 527"
            "d": _iso_date(_clean(raw.get("decision_date"))),
            "y": int(_clean(raw.get("year")) or year),
            "j": _clean(raw.get("judge")),
            "dn": _clean(raw.get("disposal_nature")),
            "path": path,
            "lang": _clean(raw.get("available_languages")),
        }
        out.append({k: v for k, v in row.items() if v not in ("", None)})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=1950)
    parser.add_argument("--to-year", type=int, default=datetime.now(timezone.utc).year)
    args = parser.parse_args()

    try:
        import pyarrow  # noqa: F401
    except ImportError:
        print("pyarrow is required: pip install pyarrow", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for year in range(args.from_year, args.to_year + 1):
        year_rows = _rows_for_year(year)
        print(f"{year}: {len(year_rows)}")
        rows.extend(year_rows)

    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        key = row.get("nc") or row["path"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    unique.sort(key=lambda r: (r.get("d") or "", r.get("nc") or ""))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT_FILE, "wt", encoding="utf-8") as fh:
        for row in unique:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    MANIFEST.write_text(
        json.dumps(
            {
                "source": "Indian Supreme Court Judgments — Dattam Labs, AWS Open Data Registry",
                "source_url": "https://registry.opendata.aws/indian-supreme-court-judgments/",
                "license": "CC BY 4.0",
                "attribution": (
                    "Judgment data: Dattam Labs, Indian Supreme Court Judgments "
                    "(AWS Open Data Registry), CC BY 4.0"
                ),
                "bucket_url": BUCKET_URL,
                "pdf_url_template": BUCKET_URL + "/data/pdf/year={year}/english/{path}_EN.pdf",
                "years": [args.from_year, args.to_year],
                "record_count": len(unique),
                "built_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(unique)} records to {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
