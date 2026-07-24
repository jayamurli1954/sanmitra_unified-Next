#!/usr/bin/env python3
"""Wire navigation-shell into app.js; bump cache v91→v92; update baseline."""
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
  initNavigationShell,
  renderModules,
  mandirNavigationItems,
  gruhaNavigationItems,
  platformNavigationItems,
  legacyBusinessNavigationItems,
  loadAndRenderGroupedNav,
  renderGroupedNav,
  renderGroupedNavFromItems,
} from "./modules/workspaces/navigation-shell.js";
'''

INIT = '''\
// Wire navigation shell + module boot renderers (avoids import cycle with app.js)
initNavigationShell({
  appRoot,
  appKeyLabel,
  topbarTitle,
  topbarSubtitle,
  topbarControlStrip,
  brandLogo,
  brandTitle,
  brandSubtitle,
  scopeTitle,
  scopeCopy,
  legacyTitle,
  legacyCopy,
  legacyVideo,
  legacyImage,
  dashboardPreview,
  nav,
  moduleList,
  escapeHtml,
  getExperienceConfig: () => experienceConfig,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getAppKey: () => APP_KEY,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  isProductionShell,
  isMandirHost,
  updateSessionUi,
  updateTrustedContextUi,
  getAccessToken,
  hasTrustedSession,
  activeOrgSelectorType,
  loadBusinessDashboardStats,
  renderDashboardPreview,
  mandirWorkspaceFromModule,
  navIconForMandirWorkspace,
  platformWorkspaceFromModule,
  syncMandirNavActiveState,
  syncGruhaNavActiveState,
  syncPlatformNavActiveState,
  syncBusinessNavActiveState,
  loadModules,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/navigation-shell.js"' in app:
        print("Already wired")
        return

    # Drop navigation.js import if unused after extract (moved into navigation-shell).
    app = re.sub(
        r'\nimport \{\n  businessNavigationGroups,\n  businessNavigationItems,\n\} from "\./modules/navigation\.js";\n',
        "\n",
        app,
        count=1,
    )

    marker = 'from "./modules/workspaces/dashboard-preview-shell.js";\n'
    if marker not in app:
        raise SystemExit("dashboard-preview-shell import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initDashboardPreviewShell({")
    if idx < 0:
        raise SystemExit("initDashboardPreviewShell not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v91",
        "app.js?v=mitrabooks-erp-v92",
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
    print(f"Wired navigation-shell; app.js={app_lines}; cache=v92")


if __name__ == "__main__":
    main()
