#!/usr/bin/env python3
"""Wire settings-workspace into app.js; bump cache v80→v81; update baseline."""
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
  initSettingsWorkspace,
  activeSettingsDetailId,
  lastBusinessAdminSettings,
  setActiveSettingsDetailId,
  setLastBusinessAdminSettings,
  settingsItemId,
  allMitraBooksSettingsItems,
  findMitraBooksSettingsItem,
  businessAdminSettingsSectionKey,
  buildBusinessAdminSettingsPayload,
  settingsStatusClass,
  renderMitraBooksSettingsCard,
  renderBusinessAdminSettingsEditor,
  renderMitraBooksSettingsDetail,
  renderMitraBooksSettingsWorkspace,
  renderProfessionalSuiteWorkspace,
  loadBusinessAdminSettings,
  saveBusinessAdminSettingsSection,
} from "./modules/workspaces/settings-workspace.js";
'''

INIT = '''\
// Wire MitraBooks settings workspace (avoids import cycle with app.js)
initSettingsWorkspace({
  escapeHtml,
  setLoginStatus,
  statusDetailText,
  renderBusinessDataHealthPanel,
  plannedOrgWorkspaceModel,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/settings-workspace.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/attachments.js";\n'
    if marker not in app:
        raise SystemExit("attachments import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initAttachments({")
    if idx < 0:
        raise SystemExit("initAttachments not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    # Keep events.js deps writable via setter (imported let is read-only from shell).
    app2, n = re.subn(
        r"set activeSettingsDetailId\(v\) \{ activeSettingsDetailId = v; \},",
        "set activeSettingsDetailId(v) { setActiveSettingsDetailId(v); },",
        app,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"events setter rewrite failed n={n}")
    app = app2

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v80",
        "app.js?v=mitrabooks-erp-v81",
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
    print(f"Wired settings-workspace; app.js={app_lines}; cache=v81")


if __name__ == "__main__":
    main()
