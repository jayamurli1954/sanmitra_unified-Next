#!/usr/bin/env python3
"""
Update MitraBooks user manual heading titles so the generated TOC includes
optional-feature notes for enterprise add-ons and OfficeMitra AI.

This is a lightweight XML string replacement to avoid re-inserting sections
and duplicating content.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCX_PATHS = [
    ROOT / "docs" / "MitraBooks_User_Manual.docx",
    ROOT / "frontend" / "assets" / "mitrabooks" / "MitraBooks_User_Manual.docx",
]


REPLACEMENTS = {
    # document.xml encodes '&' as '&amp;' in w:t. Replacement values must
    # stay XML-escaped, and must not match already-updated titles.
    "22. HR &amp; Payroll</w:t>": "22. HR &amp; Payroll (Optional add-on)</w:t>",
    "23. Manufacturing &amp; Cost Centres</w:t>": "23. Manufacturing &amp; Cost Centres (Optional add-on)</w:t>",
    "24. OfficeMitra AI</w:t>": "24. OfficeMitra AI (Optional module)</w:t>",
}


def update_docx(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing docx: {path}")

    # Read + replace in word/document.xml only; keep other parts intact.
    with zipfile.ZipFile(path, "r") as zin:
        xml = zin.read("word/document.xml").decode("utf-8", errors="ignore")

    updated = False
    for old, new in REPLACEMENTS.items():
        if old in xml:
            xml = xml.replace(old, new)
            updated = True

    if not updated:
        # Don't rewrite if nothing changed.
        return

    # Re-pack preserving filenames.
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
        for item in zin.infolist():
            name = item.filename
            data = zin.read(name)
            if name == "word/document.xml":
                data = xml.encode("utf-8")
            zout.writestr(item, data)

    tmp_path.replace(path)
    print(f"Updated optional notes in: {path}")


def main() -> None:
    for p in DOCX_PATHS:
        update_docx(p)


if __name__ == "__main__":
    main()

