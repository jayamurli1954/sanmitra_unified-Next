#!/usr/bin/env python3
"""Extract business entry helpers (Phase 3 seam 64)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/business-entry-helpers.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

HEADER = '''\
// ====================================================================
// SECTION: BUSINESS ENTRY HELPERS — TDS, roles, reversal, focus
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessEntryHelpers(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** Cached TDS/TCS section masters from GET /business/tds/sections. */
let tdsSectionsCache = null;

export function initBusinessEntryHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessEntryHelpers() must be called before using business entry helpers");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function escapeHtml(...args) { return requireDeps().escapeHtml(...args); }
function todayIsoDate(...args) { return requireDeps().todayIsoDate(...args); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }

export function hasTdsSectionsCache() {
  return !!tdsSectionsCache;
}

'''

EXPORT_FUNCS = [
    "loadTdsSections",
    "tdsSectionRate",
    "tdsSectionOptions",
    "isBusinessAdmin",
    "isCaViewer",
    "round2",
    "reversalDateBounds",
    "reversalPanel",
    "focusBusinessEntryField",
]

IMPORT = '''\
import {
  initBusinessEntryHelpers,
  hasTdsSectionsCache,
  loadTdsSections,
  tdsSectionRate,
  tdsSectionOptions,
  isBusinessAdmin,
  isCaViewer,
  round2,
  reversalDateBounds,
  reversalPanel,
  focusBusinessEntryField,
} from "./modules/workspaces/business-entry-helpers.js";
'''

INIT = '''\
// Wire business entry helpers (avoids import cycle with app.js)
initBusinessEntryHelpers({
  apiRequest,
  escapeHtml,
  todayIsoDate,
  getLastModuleContext: () => lastModuleContext,
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
    block = block.replace("lastModuleContext?", "getLastModuleContext()?")
    block = block.replace("lastModuleContext.", "getLastModuleContext().")
    # isBusinessAdmin / isCaViewer use lastModuleContext?.role — already handled by ?
    # Also bare lastModuleContext in String(... lastModuleContext?.role
    block = re.sub(r"(?<![.\w])lastModuleContext(?!\s*=)", "getLastModuleContext()", block)
    for name in ("LastModuleContext",):
        block = block.replace(f"get{name}()()", f"get{name}()")
    return block


def main() -> None:
    if OUT.exists() and "export async function loadTdsSections" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Remove let tdsSectionsCache = null; (lives in module now)
    cache_idx = next(i for i, l in enumerate(lines) if l.strip() == "let tdsSectionsCache = null;")
    del lines[cache_idx]
    while cache_idx < len(lines) and lines[cache_idx].strip() == "":
        del lines[cache_idx]
    # Also drop the TDS comment banner just above if present
    if cache_idx > 0 and "TDS/TCS section masters" in lines[cache_idx - 1]:
        del lines[cache_idx - 1]

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
        "// ========== Business Module: Typed Vouchers ==========\n",
        "// Business entry helpers live in modules/workspaces/business-entry-helpers.js\n"
        "// ========== Business Module: Typed Vouchers ==========\n",
        1,
    )

    # Fix hasTdsSectionsCache deps that referenced local cache
    app = app.replace(
        "hasTdsSectionsCache: () => !!tdsSectionsCache,",
        "hasTdsSectionsCache,",
    )

    marker = 'from "./modules/workspaces/shared-render-utils.js";\n'
    if marker not in app:
        raise SystemExit("shared-render-utils import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # Init near other business wires — before initAccountSelector is fine
    idx = app.find("initAccountSelector({")
    if idx < 0:
        raise SystemExit("initAccountSelector not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(r"app\.js\?v=mitrabooks-erp-v101", "app.js?v=mitrabooks-erp-v102", html, count=1)
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    # Keep cache-version contract test in sync
    test_path = ROOT / "tests/test_mitrabooks_frontend_local_api.py"
    test = test_path.read_text(encoding="utf-8")
    test2, tn = re.subn(
        r'assert "app\.js\?v=mitrabooks-erp-v101" in index_source',
        'assert "app.js?v=mitrabooks-erp-v102" in index_source',
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
    print(f"Wired business-entry-helpers; app.js={app_lines}; cache=v102")


if __name__ == "__main__":
    main()
