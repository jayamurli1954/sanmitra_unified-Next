#!/usr/bin/env python3
"""Wire auth-session into app.js; bump cache v88→v89; update baseline."""
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
  initAuthSession,
  hasTrustedSession,
  updateSessionUi,
  compactAccountLabel,
  signOutAndReturnToLogin,
  closeAccountMenu,
  openPasswordDialog,
  loadCurrentUserProfile,
  completeWorkspaceSignIn,
  updateCurrentPassword,
  activeOrgSelectorType,
  syncOrgSelectorOptions,
  updateTrustedContextUi,
  signInWithPassword,
} from "./modules/workspaces/auth-session.js";
'''

INIT = '''\
// Wire auth + session helpers (avoids import cycle with app.js)
initAuthSession({
  appRoot,
  sessionPill,
  topbarUser,
  topbarAvatar,
  sidebarAvatar,
  sidebarUserName,
  sidebarUserRole,
  loginEmail,
  loginPassword,
  tokenInput,
  accountMenuPanel,
  accountMenuTrigger,
  passwordForm,
  passwordStatus,
  passwordDialog,
  currentPasswordInput,
  newPasswordInput,
  confirmNewPasswordInput,
  currentOrgType,
  currentOrgTenant,
  dashboardPreview,
  apiOutput,
  moduleState,
  getAccessToken,
  getRefreshToken,
  clearAllTokens,
  clearAccessToken,
  setAccessToken,
  setRefreshToken,
  getCurrentExperience: () => currentExperience,
  setCurrentExperience: (value) => { currentExperience = value; },
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getSelectedOrgType: () => selectedOrgType,
  getOrgSelectorMeta: () => orgSelectorMeta,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  getAppKey: () => APP_KEY,
  getLoginEmailStorageKey: () => LOGIN_EMAIL_STORAGE_KEY,
  getDefaultMitraBooksLoginEmail: () => DEFAULT_MITRABOOKS_LOGIN_EMAIL,
  getLoginRequestTimeoutMs: () => LOGIN_REQUEST_TIMEOUT_MS,
  apiRequest,
  renderJson,
  setLoginStatus,
  setAuthPanelMode,
  statusDetailText,
  escapeHtml,
  setLastBusinessAccounts,
  setLastBusinessParties,
  clearVoucherListState,
  setLastAccountingDrilldown,
  renderModules,
  renderModuleState,
  initialExperience,
  mandirPublicPaymentPageUrl,
  loadAndRenderGroupedNav,
  showMandirSplash,
  hideMandirSplash,
  runChecks,
  delay,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/auth-session.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/business-reports-hub.js";\n'
    if marker not in app:
        raise SystemExit("business-reports-hub import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initBusinessReportsHub({")
    if idx < 0:
        raise SystemExit("initBusinessReportsHub not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v88",
        "app.js?v=mitrabooks-erp-v89",
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
    print(f"Wired auth-session; app.js={app_lines}; cache=v89")


if __name__ == "__main__":
    main()
