#!/usr/bin/env python3
"""Extract runChecks + platform dashboard load + setExperience (Phase 3 seam 61)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/shell-boot.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"
TEST = ROOT / "tests/test_mitrabooks_frontend_local_api.py"

HEADER = '''\
// ====================================================================
// SECTION: SHELL BOOT — runChecks + platform dashboard + setExperience
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initShellBoot(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let healthPill;
let apiOutput;
let moduleState;
let dashboardPreview;

export function initShellBoot(injected) {
  deps = injected;
  healthPill = injected.healthPill;
  apiOutput = injected.apiOutput;
  moduleState = injected.moduleState;
  dashboardPreview = injected.dashboardPreview;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initShellBoot() must be called before using shell boot helpers");
  }
  return deps;
}

function getAccessToken(...args) { return requireDeps().getAccessToken(...args); }
function clearAllTokens(...args) { return requireDeps().clearAllTokens(...args); }
function loadHealth(...args) { return requireDeps().loadHealth(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }
function statusLabel(...args) { return requireDeps().statusLabel(...args); }
function moduleItemsFromPayload(...args) { return requireDeps().moduleItemsFromPayload(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function renderModuleState(...args) { return requireDeps().renderModuleState(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function updateSessionUi(...args) { return requireDeps().updateSessionUi(...args); }
function renderModules(...args) { return requireDeps().renderModules(...args); }
function setLoginStatus(...args) { return requireDeps().setLoginStatus(...args); }
function isPasswordRecoveryPanelOpen(...args) { return requireDeps().isPasswordRecoveryPanelOpen(...args); }
function isPlatformOwnerContext(...args) { return requireDeps().isPlatformOwnerContext(...args); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderPlatformDashboard(...args) { return requireDeps().renderPlatformDashboard(...args); }
function syncPlatformNavActiveState(...args) { return requireDeps().syncPlatformNavActiveState(...args); }
function loadMandirDashboard(...args) { return requireDeps().loadMandirDashboard(...args); }
function loadGruhaDashboard(...args) { return requireDeps().loadGruhaDashboard(...args); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessPartiesForHealth(...args) { return requireDeps().loadBusinessPartiesForHealth(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function refreshBooksHealthWidget(...args) { return requireDeps().refreshBooksHealthWidget(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function emptyPlatformDashboardPayload(...args) { return requireDeps().emptyPlatformDashboardPayload(...args); }
function loadAndRenderGroupedNav(...args) { return requireDeps().loadAndRenderGroupedNav(...args); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function setCurrentExperience(value) { requireDeps().setCurrentExperience(value); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getLastPlatformOwnerDashboard() { return requireDeps().getLastPlatformOwnerDashboard(); }
function setLastPlatformOwnerDashboard(value) { requireDeps().setLastPlatformOwnerDashboard(value); }
function getActivePlatformWorkspace() { return requireDeps().getActivePlatformWorkspace(); }
function setActivePlatformWorkspace(value) { requireDeps().setActivePlatformWorkspace(value); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function getAppKey() { return requireDeps().getAppKey(); }

'''

EXPORT_FUNCS = [
    "runChecks",
    "loadPlatformOwnerDashboard",
    "setExperience",
]

IMPORT = '''\
import {
  initShellBoot,
  runChecks,
  loadPlatformOwnerDashboard,
  setExperience,
} from "./modules/workspaces/shell-boot.js";
'''

INIT = '''\
// Wire shell boot helpers (avoids import cycle with app.js)
initShellBoot({
  healthPill,
  apiOutput,
  moduleState,
  dashboardPreview,
  getAccessToken,
  clearAllTokens,
  loadHealth,
  loadModules,
  statusLabel,
  moduleItemsFromPayload,
  renderJson,
  renderModuleState,
  updateTrustedContextUi,
  updateSessionUi,
  renderModules,
  setLoginStatus,
  isPasswordRecoveryPanelOpen,
  isPlatformOwnerContext,
  apiRequest,
  renderPlatformDashboard,
  syncPlatformNavActiveState,
  loadMandirDashboard,
  loadGruhaDashboard,
  loadBusinessAccounts,
  loadBusinessPartiesForHealth,
  loadAccountingDrilldownResult,
  refreshBooksHealthWidget,
  renderDashboardPreview,
  emptyPlatformDashboardPayload,
  loadAndRenderGroupedNav,
  getCurrentExperience: () => currentExperience,
  setCurrentExperience: (value) => { currentExperience = value; },
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getLastPlatformOwnerDashboard: () => lastPlatformOwnerDashboard,
  setLastPlatformOwnerDashboard: (value) => { lastPlatformOwnerDashboard = value; },
  getActivePlatformWorkspace: () => activePlatformWorkspace,
  setActivePlatformWorkspace: (value) => { activePlatformWorkspace = value; },
  getExperienceConfig: () => experienceConfig,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  getAppKey: () => APP_KEY,
});
'''


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if re.match(rf"^(async )?function {re.escape(name)}\b", l))
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    # Longer tokens first
    block = block.replace("EXPERIENCE_APP_KEYS", "getExperienceAppKeys()")
    block = block.replace("APP_KEY", "getAppKey()")
    block = block.replace("experienceConfig", "getExperienceConfig()")
    block = block.replace("lastPlatformOwnerDashboard", "getLastPlatformOwnerDashboard()")
    block = block.replace("lastModuleContext", "getLastModuleContext()")
    block = block.replace("activePlatformWorkspace", "getActivePlatformWorkspace()")
    block = block.replace("currentExperience", "getCurrentExperience()")

    for name in (
        "ExperienceAppKeys",
        "AppKey",
        "ExperienceConfig",
        "LastPlatformOwnerDashboard",
        "LastModuleContext",
        "ActivePlatformWorkspace",
        "CurrentExperience",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")

    # Assignments
    block = re.sub(
        r"getCurrentExperience\(\) = ([^;]+);",
        r"setCurrentExperience(\1);",
        block,
    )
    block = re.sub(
        r"getLastModuleContext\(\) = ([^;]+);",
        r"setLastModuleContext(\1);",
        block,
    )
    block = re.sub(
        r"getLastPlatformOwnerDashboard\(\) = ([^;]+);",
        r"setLastPlatformOwnerDashboard(\1);",
        block,
    )
    block = re.sub(
        r"getActivePlatformWorkspace\(\) = ([^;]+);",
        r"setActivePlatformWorkspace(\1);",
        block,
    )
    return block


def main() -> None:
    if OUT.exists() and "export async function runChecks" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    block = "".join(chunks[name] for name in EXPORT_FUNCS)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = rewrite_block(block)
    if re.search(r"get\w+\(\) =(?!=)", block):
        raise SystemExit("unfixed getter assignment remains")

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.write_text(module, encoding="utf-8", newline="\n")

    app = "".join(lines)
    app = app.replace(
        "// Journal voucher posting lives in modules/workspaces/voucher-create.js\n"
        "// (createJournalVoucher). An orphaned mid-function remnant was removed here.\n",
        "// Journal voucher posting lives in modules/workspaces/voucher-create.js\n"
        "// (createJournalVoucher). An orphaned mid-function remnant was removed here.\n"
        "// Shell boot (runChecks / setExperience / platform dashboard) lives in modules/workspaces/shell-boot.js\n",
        1,
    )

    marker = 'from "./modules/workspaces/org-workspace.js";\n'
    if marker not in app:
        raise SystemExit("org-workspace import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initOrgWorkspace({")
    if idx < 0:
        raise SystemExit("initOrgWorkspace not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v98", "app.js?v=mitrabooks-erp-v99", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    test = TEST.read_text(encoding="utf-8")
    test = test.replace(
        '    run_start = app_source.index("async function runChecks()")\n'
        '    run_end = app_source.index("async function loadPlatformOwnerDashboard()", run_start)\n'
        '    run_block = app_source[run_start:run_end]\n',
        '    boot_source = (\n'
        '        REPO_ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "shell-boot.js"\n'
        '    ).read_text(encoding="utf-8")\n'
        '    run_start = boot_source.index("export async function runChecks()")\n'
        '    run_end = boot_source.index("export async function loadPlatformOwnerDashboard()", run_start)\n'
        '    run_block = boot_source[run_start:run_end]\n',
        1,
    )
    TEST.write_text(test, encoding="utf-8", newline="\n")

    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Wired shell-boot; app.js={app_lines}; cache=v99")


if __name__ == "__main__":
    main()
