#!/usr/bin/env python3
"""Wire initEventHandlers into app.js after debit-notes init; bump cache; list deps."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
EVENTS = ROOT / "frontend/mitrabooks-erp/modules/events.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

ASSIGNED = {
    "activeReceiptPreviewObjectUrl",
    "activeSettingsDetailId",
    "caClientDraft",
    "caInviteError",
    "caInviteSuccess",
    "caPracticeFilters",
    "coaTypeFilter",
    "faFormOpen",
    "mfgBudgetVsActual",
    "mfgCompleteFor",
    "mfgError",
    "mfgPlFrom",
    "mfgPlTo",
    "mfgTab",
    "mfgWoActualDraft",
}


def main() -> None:
    events = EVENTS.read_text(encoding="utf-8")
    # Ignore comment/doc mentions of deps.* (e.g. historical deps.NAME wording).
    events_code = re.sub(r"/\*.*?\*/", " ", events, flags=re.S)
    events_code = re.sub(r"//.*?$", " ", events_code, flags=re.M)
    used = sorted(set(re.findall(r"\bdeps\.([A-Za-z_][A-Za-z0-9_]*)\b", events_code)))
    used = [n for n in used if n != "deps"]

    app = APP.read_text(encoding="utf-8")
    if "initEventHandlers" in app and "from \"./modules/events.js\"" in app:
        print("Already wired")
        return

    # Import after debit-notes import block
    import_block = (
        'import { initEventHandlers } from "./modules/events.js";\n'
    )
    marker = 'from "./modules/documents/debit-notes.js";\n'
    if marker not in app:
        raise SystemExit("debit-notes import marker not found")
    app = app.replace(marker, marker + "\n" + import_block, 1)

    lines = []
    for name in used:
        if name in ASSIGNED:
            lines.append(f"  get {name}() {{ return {name}; }},")
            lines.append(f"  set {name}(v) {{ {name} = v; }},")
        else:
            lines.append(f"  {name},")
    init_call = (
        "\n// Wire workspace event handlers (avoids import cycle with app.js)\n"
        "initEventHandlers({\n"
        + "\n".join(lines)
        + "\n});\n"
    )

    insert_after = "initDebitNotes({\n"
    # Find end of initDebitNotes call
    idx = app.find("// Wire debit notes workspace")
    if idx < 0:
        raise SystemExit("debit notes wire block not found")
    # insert after initDebitNotes(...); closing
    end = app.find("});\n", app.find("initDebitNotes({", idx))
    if end < 0:
        raise SystemExit("initDebitNotes closing not found")
    end += len("});\n")
    app = app[:end] + init_call + app[end:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v48",
        "app.js?v=mitrabooks-erp-v49",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed (n={n})")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    app_lines = sum(1 for _ in APP.open(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"Wired initEventHandlers with {len(used)} deps ({len(ASSIGNED)} mutable)")
    print(f"Cache -> v49; app.js baseline -> {app_lines}")


if __name__ == "__main__":
    main()
