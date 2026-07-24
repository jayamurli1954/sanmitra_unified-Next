#!/usr/bin/env python3
"""Extract MitraBooks settings workspace into modules/workspaces/settings-workspace.js (Phase 3 seam 44)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/settings-workspace.js"

HEADER = '''\
// ====================================================================
// SECTION: MITRABOOKS SETTINGS WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initSettingsWorkspace(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let activeSettingsDetailId = "";
export let lastBusinessAdminSettings = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initSettingsWorkspace(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initSettingsWorkspace() must be called before using settings workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { return requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function renderBusinessDataHealthPanel() { return requireDeps().renderBusinessDataHealthPanel(); }
function plannedOrgWorkspaceModel(orgType) { return requireDeps().plannedOrgWorkspaceModel(orgType); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setActiveSettingsDetailId(value) {
  activeSettingsDetailId = String(value || "");
}

export function setLastBusinessAdminSettings(value) {
  lastBusinessAdminSettings = value;
}

'''

EXPORT_FUNCS = [
    "settingsItemId",
    "allMitraBooksSettingsItems",
    "findMitraBooksSettingsItem",
    "businessAdminSettingsSectionKey",
    "buildBusinessAdminSettingsPayload",
    "settingsStatusClass",
    "renderMitraBooksSettingsCard",
    "renderBusinessAdminSettingsEditor",
    "renderMitraBooksSettingsDetail",
    "renderMitraBooksSettingsWorkspace",
    "renderProfessionalSuiteWorkspace",
    "loadBusinessAdminSettings",
    "saveBusinessAdminSettingsSection",
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


def extract_const_block(text: str, name: str) -> tuple[str, str]:
    pattern = rf"(?ms)^(?:export )?const {re.escape(name)} = .*?;\n"
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"const {name} not found")
    block = m.group(0)
    return block, text[: m.start()] + text[m.end() :]


def main() -> None:
    if OUT.exists() and "export function renderMitraBooksSettingsWorkspace" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    text = APP.read_text(encoding="utf-8")

    # Drop shell state that moves into the module.
    text2, n = re.subn(
        r"(?m)^let activeSettingsDetailId = \"\";\nlet lastBusinessAdminSettings = null;\n\n",
        "",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"settings state removal failed n={n}")
    text = text2

    groups, text = extract_const_block(text, "MITRABOOKS_SETTINGS_GROUPS")
    phases, text = extract_const_block(text, "MITRABOOKS_COMPLETION_PHASES")
    keys, text = extract_const_block(text, "BUSINESS_ADMIN_SETTINGS_SECTION_KEYS")

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

    block = re.sub(
        r"(?m)^(\s*)lastBusinessAdminSettings = (.+);$",
        r"\1setLastBusinessAdminSettings(\2);",
        block,
    )
    block = block.replace(
        'currentExperience === "mitrabooks" && activeBusinessWorkspace === "settings"',
        'getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "settings"',
    )
    block = block.replace(
        "dashboardPreview.innerHTML = renderBusinessWorkspace();",
        "getDashboardPreview().innerHTML = renderBusinessWorkspace();",
    )

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    # Shell assignments to moved state
    text = text.replace('activeSettingsDetailId = "";', 'setActiveSettingsDetailId("");')

    module = (
        HEADER
        + groups.replace("const MITRABOOKS", "const MITRABOOKS", 1)
        + "\n"
        + phases
        + "\n"
        + keys
        + "\n"
        + block
    )
    if not module.endswith("\n"):
        module += "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
