#!/usr/bin/env python3
"""Extract org / planned-suite workspace renderers (Phase 3 seam 59)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/org-workspace.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

HEADER = '''\
// ====================================================================
// SECTION: ORG / PLANNED-SUITE WORKSPACE RENDERERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initOrgWorkspace(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initOrgWorkspace(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initOrgWorkspace() must be called before using org workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function renderCaPracticePortalWorkspace(...args) { return requireDeps().renderCaPracticePortalWorkspace(...args); }
function renderProfessionalSuiteWorkspace(...args) { return requireDeps().renderProfessionalSuiteWorkspace(...args); }
function renderCaDocumentIntake(...args) { return requireDeps().renderCaDocumentIntake(...args); }

'''

EXPORT_FUNCS = [
    "plannedOrgWorkspaceModel",
    "renderSelectedOrgWorkspace",
]

IMPORT = '''\
import {
  initOrgWorkspace,
  plannedOrgWorkspaceModel,
  renderSelectedOrgWorkspace,
} from "./modules/workspaces/org-workspace.js";
'''

INIT = '''\
// Wire org / planned-suite workspace renderers (avoids import cycle with app.js)
initOrgWorkspace({
  escapeHtml,
  activeOrgSelectorType,
  renderCaPracticePortalWorkspace,
  renderProfessionalSuiteWorkspace,
  renderCaDocumentIntake,
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


def main() -> None:
    if OUT.exists() and "export function renderSelectedOrgWorkspace" in OUT.read_text(encoding="utf-8"):
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

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.write_text(module, encoding="utf-8", newline="\n")

    app = "".join(lines)
    app = app.replace(
        "// Shared business attachment helpers (invoices, bills, CA documents)\n",
        "// Shared business attachment helpers (invoices, bills, CA documents)\n"
        "// Org / planned-suite workspace renderers live in modules/workspaces/org-workspace.js\n",
        1,
    )

    marker = 'from "./modules/workspaces/navigation-shell.js";\n'
    if marker not in app:
        raise SystemExit("navigation-shell import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initNavigationShell({")
    if idx < 0:
        raise SystemExit("initNavigationShell not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v96", "app.js?v=mitrabooks-erp-v97", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Wired org-workspace; app.js={app_lines}; cache=v97")


if __name__ == "__main__":
    main()
