#!/usr/bin/env python3
"""Print TOC entries from section 21 onward and sync asset copy."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "MitraBooks_User_Manual.docx"
ASSET = ROOT / "frontend" / "assets" / "mitrabooks" / "MitraBooks_User_Manual.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def main() -> None:
    xml = zipfile.ZipFile(MANUAL).read("word/document.xml")
    root = etree.fromstring(xml)
    print("=== FINAL TOC (21+) ===")
    for sdt in root.iter(f"{W}sdt"):
        alias = sdt.find(f".//{W}alias")
        if alias is None or alias.get(f"{W}val") != "Table of Contents":
            continue
        for para in sdt.iter(f"{W}p"):
            texts = [t.text or "" for t in para.iter(f"{W}t")]
            if texts and texts[0].startswith(
                ("21.", "22.", "23.", "24.", "25.", "26.", "27.", "28.")
            ):
                page = texts[1] if len(texts) > 1 else "?"
                print(f"{texts[0]:55} p.{page}")
        break
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANUAL, ASSET)
    print(f"Asset copy synced: {ASSET}")


if __name__ == "__main__":
    main()
