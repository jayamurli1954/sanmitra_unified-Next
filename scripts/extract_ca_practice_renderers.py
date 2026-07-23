#!/usr/bin/env python3
"""Append CA practice renderers into modules/workspaces/ca-practice.js (Phase 3 seam 34)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
MOD = ROOT / "frontend/mitrabooks-erp/modules/workspaces/ca-practice.js"

HELPER_FUNCS = [
    "caDocumentStatusLabel",
    "nextCaDocumentStatus",
    "caDocumentMetrics",
    "caDocumentPriorityLabel",
    "caPracticeSummary",
    "caClientComplianceLabel",
    "caClientSwitchRows",
    "caClientById",
    "caPracticeClientBreakdown",
]

RENDER_FUNCS = [
    "renderCaPracticeFilters",
    "renderCaClientMaster",
    "renderCaPracticeOperations",
    "renderCaDocumentTable",
    "renderCaDocumentIntake",
    "renderCaStatusPill",
    "renderCaAccessManagementSection",
    "renderCaViewerPortal",
    "renderCaPracticePortalWorkspace",
]

EXPORT_FUNCS = HELPER_FUNCS + RENDER_FUNCS

DEPS_HELPERS = '''\
function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function uploadBusinessAttachmentFiles(ownerType, ownerId, files) {
  return requireDeps().uploadBusinessAttachmentFiles(ownerType, ownerId, files);
}
function isCaViewer() { return requireDeps().isCaViewer(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function plannedOrgWorkspaceModel(orgType) { return requireDeps().plannedOrgWorkspaceModel(orgType); }

'''


def find_fn_block(lines: list[str], signature: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if signature in l and l.lstrip().startswith(("function ", "async function "))
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
        raise SystemExit(f"unterminated function for {signature}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def extract_blocks(lines: list[str], names: list[str]) -> tuple[str, list[str]]:
    """Extract named functions (high→low index) and return joined text + remaining lines."""
    spans: list[tuple[int, int, str]] = []
    for name in names:
        start, end = find_fn_block(lines, f"function {name}")
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]
    ordered = "".join(chunks[name] for name in names)
    return ordered, lines


def main() -> None:
    if "export function renderCaPracticePortalWorkspace" in MOD.read_text(encoding="utf-8"):
        print("Renderers already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    helpers_text, lines = extract_blocks(lines, HELPER_FUNCS)
    renders_text, lines = extract_blocks(lines, RENDER_FUNCS)

    block = helpers_text + renders_text
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

    # Drop orphaned CA section banner if it now sits above attachment helpers only
    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: CA PRACTICE PORTAL \+ DOCUMENT INTAKE\n.*?^// ═+\n\n+",
        "// Shared business attachment helpers (invoices, bills, CA documents)\n\n",
        text,
        count=1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")

    mod = MOD.read_text(encoding="utf-8")
    # Update header comment
    mod = mod.replace(
        "// CA renderers remain in app.js for a later seam.\n",
        "// Includes CA practice renderers (Phase 3 seam 34).\n",
    )
    # Inject deps helpers after existing requireDeps wrappers (before setters)
    anchor = "function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }\n"
    if anchor not in mod:
        raise SystemExit("listBusinessAttachments deps anchor not found")
    if "function escapeHtml(value)" not in mod:
        mod = mod.replace(anchor, anchor + "\n" + DEPS_HELPERS, 1)

    if not mod.endswith("\n"):
        mod += "\n"
    mod += "\n// --- CA practice renderers (seam 34) ---\n\n" + block
    if not mod.endswith("\n"):
        mod += "\n"

    MOD.write_text(mod, encoding="utf-8", newline="\n")
    print(f"Updated {MOD.relative_to(ROOT)} ({len(mod.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
