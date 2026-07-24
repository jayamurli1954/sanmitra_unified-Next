#!/usr/bin/env python3
"""Extract navigation shell + module boot renderers (Phase 3 seam 55)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/navigation-shell.js"

HEADER = '''\
// ====================================================================
// SECTION: NAVIGATION SHELL + MODULE BOOT RENDERERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initNavigationShell(...).
// Business nav group config stays in modules/navigation.js.
// ====================================================================

import {
  businessNavigationGroups,
  businessNavigationItems,
} from "../navigation.js";

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let appRoot;
let appKeyLabel;
let topbarTitle;
let topbarSubtitle;
let topbarControlStrip;
let brandLogo;
let brandTitle;
let brandSubtitle;
let scopeTitle;
let scopeCopy;
let legacyTitle;
let legacyCopy;
let legacyVideo;
let legacyImage;
let dashboardPreview;
let nav;
let moduleList;

export function initNavigationShell(injected) {
  deps = injected;
  appRoot = injected.appRoot;
  appKeyLabel = injected.appKeyLabel;
  topbarTitle = injected.topbarTitle;
  topbarSubtitle = injected.topbarSubtitle;
  topbarControlStrip = injected.topbarControlStrip;
  brandLogo = injected.brandLogo;
  brandTitle = injected.brandTitle;
  brandSubtitle = injected.brandSubtitle;
  scopeTitle = injected.scopeTitle;
  scopeCopy = injected.scopeCopy;
  legacyTitle = injected.legacyTitle;
  legacyCopy = injected.legacyCopy;
  legacyVideo = injected.legacyVideo;
  legacyImage = injected.legacyImage;
  dashboardPreview = injected.dashboardPreview;
  nav = injected.nav;
  moduleList = injected.moduleList;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initNavigationShell() must be called before using navigation shell helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getAppKey() { return requireDeps().getAppKey(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function isProductionShell(...args) { return requireDeps().isProductionShell(...args); }
function isMandirHost(...args) { return requireDeps().isMandirHost(...args); }
function updateSessionUi(...args) { return requireDeps().updateSessionUi(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function getAccessToken(...args) { return requireDeps().getAccessToken(...args); }
function hasTrustedSession(...args) { return requireDeps().hasTrustedSession(...args); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function loadBusinessDashboardStats(...args) { return requireDeps().loadBusinessDashboardStats(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function mandirWorkspaceFromModule(...args) { return requireDeps().mandirWorkspaceFromModule(...args); }
function navIconForMandirWorkspace(...args) { return requireDeps().navIconForMandirWorkspace(...args); }
function platformWorkspaceFromModule(...args) { return requireDeps().platformWorkspaceFromModule(...args); }
function syncMandirNavActiveState(...args) { return requireDeps().syncMandirNavActiveState(...args); }
function syncGruhaNavActiveState(...args) { return requireDeps().syncGruhaNavActiveState(...args); }
function syncPlatformNavActiveState(...args) { return requireDeps().syncPlatformNavActiveState(...args); }
function syncBusinessNavActiveState(...args) { return requireDeps().syncBusinessNavActiveState(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }

'''

EXPORT_FUNCS = [
    "renderModules",
    "mandirNavigationItems",
    "gruhaNavigationItems",
    "platformNavigationItems",
    "legacyBusinessNavigationItems",
    "loadAndRenderGroupedNav",
    "renderGroupedNav",
    "renderGroupedNavFromItems",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l)
    )
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if "{" in line or "}" in line:
            depth += line.count("{") - line.count("}")
            started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    # Longer tokens first to avoid APP_KEY substring collisions.
    block = block.replace("EXPERIENCE_APP_KEYS", "getExperienceAppKeys()")
    block = block.replace("APP_KEY", "getAppKey()")
    block = block.replace("activeBusinessWorkspace", "getActiveBusinessWorkspace()")
    block = block.replace("currentExperience", "getCurrentExperience()")
    block = block.replace("experienceConfig", "getExperienceConfig()")

    for name in (
        "ExperienceAppKeys",
        "AppKey",
        "ActiveBusinessWorkspace",
        "CurrentExperience",
        "ExperienceConfig",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")

    return block


def main() -> None:
    if OUT.exists() and "export function renderModules" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    # Drop section banners that only framed the extracted block.
    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: EXPERIENCE \+ MODULE CONFIG\n.*?^// ═+\n\n+",
        "// Navigation shell + module boot renderers live in modules/workspaces/navigation-shell.js\n\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Load grouped navigation from /api/v1/modules/me \(Phase 1D\).*?\*/\n",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Render navigation with group headers \(Phase 1D\).*?\*/\n\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: NAVIGATION RENDERING\n.*?^// ═+\n\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Fallback: Render hardcoded navigation items.*?\*/\n",
        "",
        text,
        count=1,
    )

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

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
