#!/usr/bin/env python3
"""Extract business list filter/pagination helpers (Phase 3 seam 45)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/business-list-filters.js"

HEADER = '''\
// ====================================================================
// SECTION: BUSINESS LIST FILTERING + PAGINATION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessListFilters(...).
// ====================================================================

export const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",
    from_date: "",
    to_date: "",
  },
  vouchers: {
    offset: 0,
    voucher_type: "",
    status: "",
    approval_status: "",
    include_reviewed: false,
  },
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initBusinessListFilters(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessListFilters() must be called before using business list filter helpers");
  }
  return deps;
}

function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function loadBusinessVouchers() { return requireDeps().loadBusinessVouchers(); }

'''

EXPORT_FUNCS = [
    "applyBusinessListFilter",
    "resetBusinessListFilter",
    "pageBusinessList",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l.lstrip())
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


def main() -> None:
    if OUT.exists() and "export function applyBusinessListFilter" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    text = APP.read_text(encoding="utf-8")

    # Remove shell businessListState (moved into module).
    text2, n = re.subn(
        r"(?ms)^const businessListState = \{\n.*?\n\};\n\n+",
        "",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"businessListState removal failed n={n}")
    text = text2

    lines = text.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
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

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: BUSINESS LIST FILTERING \+ PAGINATION\n.*?^// ═+\n\n+",
        "// Business list filtering lives in modules/workspaces/business-list-filters.js\n\n",
        text,
        count=1,
    )

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
