#!/usr/bin/env python3
"""
DOCX repair helper:
Word/ppt/docx stores '&' as '&amp;' inside word/document.xml.

Our optional-feature heading updater replaced strings without escaping '&',
creating invalid XML entities that Word refuses to open.

This script re-packages the DOCX and escapes the known invalid heading text.
"""

from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    ROOT / "docs" / "MitraBooks_User_Manual.docx",
    ROOT / "frontend" / "assets" / "mitrabooks" / "MitraBooks_User_Manual.docx",
]

REPLACEMENTS = {
    "22. HR & Payroll (Optional add-on)": "22. HR &amp; Payroll (Optional add-on)",
    "23. Manufacturing & Cost Centres (Optional add-on)": "23. Manufacturing &amp; Cost Centres (Optional add-on)",
}


def repair_one(src: Path) -> Path:
    if not src.exists():
        raise SystemExit(f"Missing DOCX: {src}")

    out = src.with_suffix(".repaired.docx")
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                xml = data.decode("utf-8", errors="ignore")
                for old, new in REPLACEMENTS.items():
                    xml = xml.replace(old, new)
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    return out


def main() -> None:
    for t in TARGETS:
        out = repair_one(t)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()

