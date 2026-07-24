#!/usr/bin/env python3
"""Wire experience-config into app.js; bump cache v92→v93; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

IMPORT = '''\
import {
  isMandirHost,
  isGruhaHost,
  isProductionShell,
  initialExperience,
  entitlementModulesByOrgType,
  orgSelectorMeta,
  experienceConfig,
} from "./modules/workspaces/experience-config.js";
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/experience-config.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/navigation-shell.js";\n'
    if marker not in app:
        raise SystemExit("navigation-shell import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # Ensure currentExperience still initializes after import.
    if "let currentExperience = initialExperience();" not in app:
        raise SystemExit("currentExperience bootstrap missing")

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v92",
        "app.js?v=mitrabooks-erp-v93",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wired experience-config; app.js={app_lines}; cache=v93")


if __name__ == "__main__":
    main()
