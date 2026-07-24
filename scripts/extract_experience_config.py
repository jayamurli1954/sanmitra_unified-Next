#!/usr/bin/env python3
"""Extract experience detection + product shell config (Phase 3 seam 56)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/experience-config.js"

HEADER = """\
// ====================================================================
// SECTION: EXPERIENCE DETECTION + PRODUCT SHELL CONFIG
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. No init wiring — leaf module with no app.js deps.
// ====================================================================

"""

EXPORT_FUNCS = [
    "isMandirHost",
    "isGruhaHost",
    "isProductionShell",
    "initialExperience",
]

EXPORT_CONSTS = [
    "entitlementModulesByOrgType",
    "orgSelectorMeta",
    "experienceConfig",
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
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def find_const_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if re.match(rf"^const {re.escape(name)}\b", l))
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        depth += lines[i].count("[") - lines[i].count("]")
        if "{" in lines[i] or "[" in lines[i] or "}" in lines[i] or "]" in lines[i]:
            started = True
        # single-line const without braces
        if not started and lines[i].rstrip().endswith(";"):
            end = i + 1
            break
        if started and depth <= 0 and lines[i].rstrip().endswith(";"):
            end = i + 1
            break
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated const for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def main() -> None:
    if OUT.exists() and "export const experienceConfig" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans: list[tuple[int, int, str, str]] = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name, "fn"))
    for name in EXPORT_CONSTS:
        start, end = find_const_block(lines, name)
        spans.append((start, end, name, "const"))
    spans.sort(key=lambda s: s[0], reverse=True)

    chunks: dict[str, str] = {}
    for start, end, name, _kind in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: EXPERIENCE DETECTION \+ PRODUCT SHELL\n.*?^// ═+\n\n+",
        "// Experience detection + product shell config live in modules/workspaces/experience-config.js\n\n",
        text,
        count=1,
    )

    order = EXPORT_FUNCS + EXPORT_CONSTS
    block = "".join(chunks[name] for name in order)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^function {name}\b",
            rf"export function {name}",
            block,
            count=1,
        )
    for name in EXPORT_CONSTS:
        block = re.sub(
            rf"(?m)^const {name}\b",
            rf"export const {name}",
            block,
            count=1,
        )

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block:
            raise SystemExit(f"export missing for {name}")
    for name in EXPORT_CONSTS:
        if f"export const {name}" not in block:
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
