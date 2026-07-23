#!/usr/bin/env python3
"""Wire initShellUi into app.js; bump cache v49→v50; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
SHELL = ROOT / "frontend/mitrabooks-erp/modules/shell-ui.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

ASSIGNED = {
    "activeBusinessWorkspace",
    "lastCaDocuments",
    "lastCaDocumentsResult",
    "selectedOrgType",
}


def main() -> None:
    shell = SHELL.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", " ", shell, flags=re.S)
    code = re.sub(r"//.*?$", " ", code, flags=re.M)
    used = sorted(set(re.findall(r"\bdeps\.([A-Za-z_][A-Za-z0-9_]*)\b", code)))

    app = APP.read_text(encoding="utf-8")
    if "initShellUi" in app and 'from "./modules/shell-ui.js"' in app:
        print("Already wired")
        return

    marker = 'import { initEventHandlers } from "./modules/events.js";\n'
    if marker not in app:
        raise SystemExit("events import marker not found")
    app = app.replace(
        marker,
        marker + 'import { initShellUi } from "./modules/shell-ui.js";\n',
        1,
    )

    lines = []
    for name in used:
        if name in ASSIGNED:
            lines.append(f"  get {name}() {{ return {name}; }},")
            lines.append(f"  set {name}(v) {{ {name} = v; }},")
        else:
            lines.append(f"  {name},")

    init_call = (
        "\n// Wire shell UI (theme toggles, sidebar org/FY, quick actions)\n"
        "initShellUi({\n"
        + "\n".join(lines)
        + "\n});\n"
    )

    theme_marker = "initializeTheme();\n"
    idx = app.find(theme_marker)
    if idx < 0:
        raise SystemExit("initializeTheme() marker not found")
    insert_at = idx + len(theme_marker)
    app = app[:insert_at] + init_call + app[insert_at:]
    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v49",
        "app.js?v=mitrabooks-erp-v50",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    app_lines = sum(1 for _ in APP.open(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"Wired initShellUi with {len(used)} deps ({len(ASSIGNED)} mutable)")
    print(f"Cache -> v50; app.js baseline -> {app_lines}")


if __name__ == "__main__":
    main()
