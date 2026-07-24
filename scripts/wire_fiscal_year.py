#!/usr/bin/env python3
"""Wire fiscal-year module into app.js; bump cache v82→v83; update baseline."""
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
  currentFinancialYear,
  recentFinancialYears,
  currentFyQuarter,
  recentFyQuarters,
  financialYearStartIso,
} from "./modules/workspaces/fiscal-year.js";
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/fiscal-year.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/business-list-filters.js";\n'
    if marker not in app:
        raise SystemExit("business-list-filters import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v82",
        "app.js?v=mitrabooks-erp-v83",
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
    print(f"Wired fiscal-year; app.js={app_lines}; cache=v83")


if __name__ == "__main__":
    main()
