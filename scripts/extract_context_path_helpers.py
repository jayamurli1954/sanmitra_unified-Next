#!/usr/bin/env python3
"""Extract tenant-context + Mandir list path helpers (Phase 3 seam 65)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/context-path-helpers.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

HEADER = '''\
// ====================================================================
// SECTION: CONTEXT + MANDIR LIST PATH HELPERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initContextPathHelpers(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initContextPathHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initContextPathHelpers() must be called before using context/path helpers");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }
function setLastBusinessPartiesResult(...args) { return requireDeps().setLastBusinessPartiesResult(...args); }
function setLastBusinessParties(...args) { return requireDeps().setLastBusinessParties(...args); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getMandirListState() { return requireDeps().getMandirListState(); }
function getMandirListPageSize() { return requireDeps().getMandirListPageSize(); }

'''

EXPORT_FUNCS = [
    "isBusinessModuleEnabled",
    "enabledModuleKeys",
    "isPlatformOwnerContext",
    "isBusinessTenantContext",
    "loadBusinessPartiesForHealth",
    "loadModuleContextForAccounts",
    "buildQueryString",
    "mandirListPath",
    "mandirPublicPaymentsPath",
    "mandirPublicPaymentExceptionsPath",
    "todayIsoDate",
]

IMPORT = '''\
import {
  initContextPathHelpers,
  isBusinessModuleEnabled,
  enabledModuleKeys,
  isPlatformOwnerContext,
  isBusinessTenantContext,
  loadBusinessPartiesForHealth,
  loadModuleContextForAccounts,
  buildQueryString,
  mandirListPath,
  mandirPublicPaymentsPath,
  mandirPublicPaymentExceptionsPath,
  todayIsoDate,
} from "./modules/workspaces/context-path-helpers.js";
'''

INIT = '''\
// Wire context + Mandir list path helpers (avoids import cycle with app.js)
initContextPathHelpers({
  apiRequest,
  loadModules,
  setLastBusinessPartiesResult,
  setLastBusinessParties,
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getMandirListState: () => mandirListState,
  getMandirListPageSize: () => MANDIR_LIST_PAGE_SIZE,
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
    # Assignments first
    block = block.replace("lastModuleContext = result.payload;", "setLastModuleContext(result.payload);")
    block = block.replace("lastModuleContext = null;", "setLastModuleContext(null);")  # unlikely
    # Reads — longer tokens first
    block = block.replace("mandirListState", "getMandirListState()")
    block = block.replace("MANDIR_LIST_PAGE_SIZE", "getMandirListPageSize()")
    block = block.replace("lastModuleContext", "getLastModuleContext()")
    for name in ("MandirListState", "MandirListPageSize", "LastModuleContext"):
        block = block.replace(f"get{name}()()", f"get{name}()")
    # Fix default-arg forms that become getX() = getX()
    block = block.replace(
        "enabledModuleKeys(context = getLastModuleContext())",
        "enabledModuleKeys(context = null)",
    )
    block = block.replace(
        "isPlatformOwnerContext(context = getLastModuleContext())",
        "isPlatformOwnerContext(context = null)",
    )
    block = block.replace(
        "isBusinessTenantContext(context = getLastModuleContext())",
        "isBusinessTenantContext(context = null)",
    )
    # At start of those functions, normalize null context
    for fname in ("enabledModuleKeys", "isPlatformOwnerContext", "isBusinessTenantContext"):
        block = re.sub(
            rf"(export function {fname}\(context = null\) \{{\n)",
            rf"\1  if (context == null) context = getLastModuleContext();\n",
            block,
            count=1,
        )
    bad = re.findall(r"get\w+\(\) =(?!=)", block)
    if bad:
        raise SystemExit(f"unfixed getter assignment remains: {bad}")
    return block


def main() -> None:
    if OUT.exists() and "export function mandirListPath" in OUT.read_text(encoding="utf-8"):
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

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.write_text(module, encoding="utf-8", newline="\n")

    app = "".join(lines)
    app = app.replace(
        "// Account helpers + data health live in modules/workspaces/account-helpers.js\n"
        "// Context helpers (platform owner / business tenant) remain below.\n\n",
        "// Account helpers + data health live in modules/workspaces/account-helpers.js\n"
        "// Context + Mandir list path helpers live in modules/workspaces/context-path-helpers.js\n\n",
        1,
    )
    app = app.replace(
        "// Mandir create forms + posting dialogs live in modules/workspaces/mandir-create-forms.js\n"
        "// Platform-owner onboarding/entitlements live in modules/workspaces/platform-owner-ops.js\n"
        "// Mandir verification/cancel dialogs live in modules/workspaces/mandir-create-forms.js\n",
        "// Context + Mandir list path helpers live in modules/workspaces/context-path-helpers.js\n"
        "// Mandir create forms + posting dialogs live in modules/workspaces/mandir-create-forms.js\n"
        "// Platform-owner onboarding/entitlements live in modules/workspaces/platform-owner-ops.js\n"
        "// Mandir verification/cancel dialogs live in modules/workspaces/mandir-create-forms.js\n",
        1,
    )

    marker = 'from "./modules/workspaces/business-entry-helpers.js";\n'
    if marker not in app:
        raise SystemExit("business-entry-helpers import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initBusinessEntryHelpers({")
    if idx < 0:
        raise SystemExit("initBusinessEntryHelpers not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v102", "app.js?v=mitrabooks-erp-v103", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    test_path = ROOT / "tests/test_mitrabooks_frontend_local_api.py"
    test = test_path.read_text(encoding="utf-8")
    test2, tn = re.subn(
        r'assert "app\.js\?v=mitrabooks-erp-v102" in index_source',
        'assert "app.js?v=mitrabooks-erp-v103" in index_source',
        test,
        count=1,
    )
    if tn != 1:
        raise SystemExit(f"cache test bump failed n={tn}")
    test_path.write_text(test2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Wired context-path-helpers; app.js={app_lines}; cache=v103")


if __name__ == "__main__":
    main()
