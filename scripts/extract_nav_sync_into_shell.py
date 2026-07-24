#!/usr/bin/env python3
"""Fold nav workspace helpers + sync into navigation-shell (Phase 3 seam 58)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
NAV = ROOT / "frontend/mitrabooks-erp/modules/workspaces/navigation-shell.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

EXPORT_FUNCS = [
    "mandirWorkspaceFromModule",
    "platformWorkspaceFromModule",
    "navIconForMandirWorkspace",
    "syncMandirNavActiveState",
    "syncGruhaNavActiveState",
    "syncPlatformNavActiveState",
]


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
    block = block.replace("activeMandirWorkspace", "getActiveMandirWorkspace()")
    block = block.replace("activeGruhaWorkspace", "getActiveGruhaWorkspace()")
    block = block.replace("activePlatformWorkspace", "getActivePlatformWorkspace()")
    block = block.replace("currentExperience", "getCurrentExperience()")
    for name in (
        "ActiveMandirWorkspace",
        "ActiveGruhaWorkspace",
        "ActivePlatformWorkspace",
        "CurrentExperience",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")
    return block


def main() -> None:
    nav_text = NAV.read_text(encoding="utf-8")
    if "export function syncMandirNavActiveState" in nav_text:
        print("Already extracted")
        return

    app_lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(app_lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(app_lines[start:end])
        del app_lines[start:end]

    app_text = "".join(app_lines)
    app_text = re.sub(
        r"(?ms)^// ═+\n// SECTION: SHARED UTILITIES\n.*?^// ═+\n\n+",
        "// Shared utilities (escapeHtml, formatters, auth status) remain below.\n"
        "// Nav workspace mapping + sync live in modules/workspaces/navigation-shell.js\n\n",
        app_text,
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

    # Remove deps wrappers now provided locally; add new getters + topbarCurrent binding.
    for name in EXPORT_FUNCS:
        nav_text = re.sub(
            rf"function {name}\(\.\.\.args\) \{{ return requireDeps\(\)\.{name}\(\.\.\.args\); \}}\n",
            "",
            nav_text,
        )

    # Bind topbarCurrent in init
    if "topbarCurrent = injected.topbarCurrent" not in nav_text:
        nav_text = nav_text.replace(
            "let moduleList;\n",
            "let moduleList;\nlet topbarCurrent;\n",
            1,
        )
        nav_text = nav_text.replace(
            "  moduleList = injected.moduleList;\n}",
            "  moduleList = injected.moduleList;\n"
            "  topbarCurrent = injected.topbarCurrent;\n}",
            1,
        )

    # Add getters after getCurrentExperience helper
    insert_helpers = (
        "function getActiveMandirWorkspace() { return requireDeps().getActiveMandirWorkspace(); }\n"
        "function getActiveGruhaWorkspace() { return requireDeps().getActiveGruhaWorkspace(); }\n"
        "function getActivePlatformWorkspace() { return requireDeps().getActivePlatformWorkspace(); }\n"
        "function updatePageHeader(...args) { return requireDeps().updatePageHeader(...args); }\n"
    )
    if "function getActiveMandirWorkspace()" not in nav_text:
        nav_text = nav_text.replace(
            "function getCurrentExperience() { return requireDeps().getCurrentExperience(); }\n",
            "function getCurrentExperience() { return requireDeps().getCurrentExperience(); }\n"
            + insert_helpers,
            1,
        )

    # Append exported helpers before end of file
    if not nav_text.endswith("\n"):
        nav_text += "\n"
    nav_text += "\n" + block
    if not nav_text.endswith("\n"):
        nav_text += "\n"

    # Update app.js import from navigation-shell
    old_import = '''import {
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
    new_import = '''import {
  initNavigationShell,
  renderModules,
  mandirNavigationItems,
  gruhaNavigationItems,
  platformNavigationItems,
  legacyBusinessNavigationItems,
  loadAndRenderGroupedNav,
  renderGroupedNav,
  renderGroupedNavFromItems,
  mandirWorkspaceFromModule,
  platformWorkspaceFromModule,
  navIconForMandirWorkspace,
  syncMandirNavActiveState,
  syncGruhaNavActiveState,
  syncPlatformNavActiveState,
} from "./modules/workspaces/navigation-shell.js";
'''
    if old_import not in app_text:
        raise SystemExit("navigation-shell import block not found")
    app_text = app_text.replace(old_import, new_import, 1)

    # Extend initNavigationShell call
    init_old = "initNavigationShell({\n  appRoot,\n"
    if init_old not in app_text:
        raise SystemExit("initNavigationShell not found")
    # Add topbarCurrent + new getters; remove obsolete function deps if present
    # Find full init block and rebuild key lines via surgical replaces.
    app_text = app_text.replace(
        "initNavigationShell({\n  appRoot,\n  appKeyLabel,\n",
        "initNavigationShell({\n  appRoot,\n  appKeyLabel,\n",
        1,
    )
    if "topbarCurrent," not in app_text[app_text.find("initNavigationShell({") : app_text.find("initNavigationShell({") + 1200]:
        app_text = app_text.replace(
            "  moduleList,\n  escapeHtml,\n",
            "  moduleList,\n  topbarCurrent,\n  escapeHtml,\n",
            1,
        )
    # Insert workspace getters after getCurrentExperience in init
    if "getActiveMandirWorkspace:" not in app_text:
        app_text = app_text.replace(
            "  getCurrentExperience: () => currentExperience,\n  getActiveBusinessWorkspace: () => activeBusinessWorkspace,\n",
            "  getCurrentExperience: () => currentExperience,\n"
            "  getActiveMandirWorkspace: () => activeMandirWorkspace,\n"
            "  getActiveGruhaWorkspace: () => activeGruhaWorkspace,\n"
            "  getActivePlatformWorkspace: () => activePlatformWorkspace,\n"
            "  updatePageHeader,\n"
            "  getActiveBusinessWorkspace: () => activeBusinessWorkspace,\n",
            1,
        )
    # Remove now-imported functions from init deps
    for line in (
        "  mandirWorkspaceFromModule,\n",
        "  navIconForMandirWorkspace,\n",
        "  platformWorkspaceFromModule,\n",
        "  syncMandirNavActiveState,\n",
        "  syncGruhaNavActiveState,\n",
        "  syncPlatformNavActiveState,\n",
    ):
        # Only strip from initNavigationShell block — first occurrence after initNavigationShell
        idx = app_text.find("initNavigationShell({")
        end = app_text.find("});", idx)
        head, mid, tail = app_text[:idx], app_text[idx:end], app_text[end:]
        mid = mid.replace(line, "")
        app_text = head + mid + tail

    NAV.write_text(nav_text, encoding="utf-8", newline="\n")
    APP.write_text(app_text, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v95", "app.js?v=mitrabooks-erp-v96", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines_count = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines_count
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Folded nav sync into navigation-shell; app.js={app_lines_count}; cache=v96")
    print(f"navigation-shell.js={len(nav_text.splitlines())} lines")


if __name__ == "__main__":
    main()
