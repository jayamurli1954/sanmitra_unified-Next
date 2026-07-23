#!/usr/bin/env python3
"""Wire CA practice renderers into app.js; bump cache v70→v71; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

IMPORT_EXTRA = """\
  caClientById,
  renderCaDocumentIntake,
  renderCaPracticePortalWorkspace,
"""

INIT_EXTRA = """\
  escapeHtml,
  renderBusinessAttachmentPanel,
  uploadBusinessAttachmentFiles,
  isCaViewer,
  isBusinessAdmin,
  plannedOrgWorkspaceModel,
"""


def main() -> None:
    app = APP.read_text(encoding="utf-8")

    if "renderCaPracticePortalWorkspace," in app and "from \"./modules/workspaces/ca-practice.js\"" in app:
        # may already be partially wired — still ensure init deps
        pass

    # Extend existing ca-practice import
    marker = "  updateCaPracticeDocumentStatus,\n} from \"./modules/workspaces/ca-practice.js\";"
    if marker not in app:
        # after seam 33 we also added setLastCa* — try alternate
        marker = "  setLastCaDocumentsResult,\n  loadCaPracticeDocuments,"
        if "renderCaPracticePortalWorkspace," not in app.split("ca-practice.js")[0][-800:]:
            # Find closing of ca-practice import and insert before it
            m = re.search(
                r'(from "\./modules/workspaces/ca-practice\.js";)',
                app,
            )
            if not m:
                raise SystemExit("ca-practice import not found")
            # Find the import block start
            start = app.rfind("import {", 0, m.start())
            block = app[start:m.end()]
            if "renderCaPracticePortalWorkspace" not in block:
                block2 = block.replace(
                    "} from \"./modules/workspaces/ca-practice.js\";",
                    IMPORT_EXTRA + "} from \"./modules/workspaces/ca-practice.js\";",
                )
                # Also ensure setLastCa* stay if present
                app = app[:start] + block2 + app[m.end():]
    else:
        app = app.replace(
            marker,
            IMPORT_EXTRA + marker,
            1,
        )

    # Deduplicate if double-inserted
    app = re.sub(
        r"(  renderCaPracticePortalWorkspace,\n)+",
        "  renderCaPracticePortalWorkspace,\n",
        app,
    )
    app = re.sub(r"(  renderCaDocumentIntake,\n)+", "  renderCaDocumentIntake,\n", app)
    app = re.sub(r"(  caClientById,\n)+", "  caClientById,\n", app)

    # Expand initCaPractice deps
    init_marker = "initCaPractice({\n  setLoginStatus,\n  statusDetailText,\n  getApiOutput: () => apiOutput,\n  getCurrentExperience: () => currentExperience,\n  getActiveBusinessWorkspace: () => activeBusinessWorkspace,\n  getDashboardPreview: () => dashboardPreview,\n  renderBusinessWorkspace: () => renderBusinessWorkspace(),\n  listBusinessAttachments,\n});"
    init_new = "initCaPractice({\n  setLoginStatus,\n  statusDetailText,\n  getApiOutput: () => apiOutput,\n  getCurrentExperience: () => currentExperience,\n  getActiveBusinessWorkspace: () => activeBusinessWorkspace,\n  getDashboardPreview: () => dashboardPreview,\n  renderBusinessWorkspace: () => renderBusinessWorkspace(),\n  listBusinessAttachments,\n" + INIT_EXTRA + "});"
    if "plannedOrgWorkspaceModel," not in app[app.find("initCaPractice({") : app.find("initCaPractice({") + 800]:
        if init_marker not in app:
            raise SystemExit("initCaPractice block not found for deps expand")
        app = app.replace(init_marker, init_new, 1)

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v70",
        "app.js?v=mitrabooks-erp-v71",
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
    print(f"Wired renderers; app.js={app_lines}; cache=v71")


if __name__ == "__main__":
    main()
