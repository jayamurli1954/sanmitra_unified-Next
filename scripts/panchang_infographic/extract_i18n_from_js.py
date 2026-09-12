"""One-off helper: sync panchang_i18n.json from frontend WhatsApp message maps."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JS_PATH = ROOT / "frontend" / "src" / "utils" / "panchangWhatsAppMessage.js"
OUT_PATH = Path(__file__).resolve().parent / "panchang_i18n.json"


def main() -> None:
    js = JS_PATH.read_text(encoding="utf-8")
    maps: dict[str, dict[str, dict[str, str]]] = {}
    for block in re.finditer(r"const (\w+) = \{([\s\S]*?)\n\};", js):
        name = block.group(1)
        if not name.endswith("_I18N"):
            continue
        body = block.group(2)
        entries: dict[str, dict[str, str]] = {}
        pattern = re.compile(
            r"(?:'([^']+)'|(\w+)):\s*\{\s*kn:\s*'([^']*)',\s*sa:\s*'([^']*)'\s*\}"
        )
        for match in pattern.finditer(body):
            key = match.group(1) or match.group(2)
            entries[key] = {"kn": match.group(3), "hi": match.group(4)}
        maps[name.replace("_I18N", "").lower()] = entries
    OUT_PATH.write_text(json.dumps(maps, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(maps)} tables)")


if __name__ == "__main__":
    main()
