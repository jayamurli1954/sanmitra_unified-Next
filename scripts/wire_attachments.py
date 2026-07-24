#!/usr/bin/env python3
"""Wire attachments module into app.js; bump cache v79→v80; update baseline."""
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
  initAttachments,
  businessAttachmentPath,
  uploadBusinessAttachmentFiles,
  listBusinessAttachments,
  attachmentListSummary,
  renderBusinessAttachmentPanel,
} from "./modules/workspaces/attachments.js";
'''

INIT = '''\
// Wire business attachments (avoids import cycle with app.js)
initAttachments({
  escapeHtml,
  getAccessToken,
  buildFrontendApiUrl,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/attachments.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/business-list-tables.js";\n'
    if marker not in app:
        raise SystemExit("business-list-tables import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initBusinessListTables({")
    if idx < 0:
        raise SystemExit("initBusinessListTables not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v79",
        "app.js?v=mitrabooks-erp-v80",
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
    print(f"Wired attachments; app.js={app_lines}; cache=v80")


if __name__ == "__main__":
    main()
