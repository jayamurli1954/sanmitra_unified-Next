#!/usr/bin/env python3
"""Extract AUDIT TRAIL into modules/workspaces/audit-trail.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/audit-trail.js"

HEADER = '''\
// ====================================================================
// SECTION: AUDIT TRAIL
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAuditTrail(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastAuditEvents = [];
export const auditListState = {
  offset: 0,
  q: "",
  entity_type: "",
  action: "",
  from_date: "",
  to_date: "",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAuditTrail(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAuditTrail() must be called before using audit-trail helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "renderAuditEventsTable",
    "renderAuditListFilters",
    "loadAuditEvents",
    "openAuditEventDetailDialog",
    "applyAuditFilters",
    "resetAuditFilters",
    "pageAuditList",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "Business Module: Audit Trail" in l or "SECTION: AUDIT TRAIL" in l)
    # Prefer the banner above state if present
    banner = next((i for i, l in enumerate(lines) if "Business Module: Audit Trail" in l), start)
    start = banner

    end = next(i for i, l in enumerate(lines) if i > start and "SECTION: GRUHAMITRA WORKSPACE" in l)
    while end > start and (
        lines[end - 1].strip() == ""
        or lines[end - 1].strip().startswith("// ═")
        or lines[end - 1].strip().startswith("// API")
        or lines[end - 1].strip().startswith("// NOTE")
    ):
        end -= 1

    # Module body starts after state decls (we'll put state in HEADER)
    # Include formatTimestampIST + section functions; strip duplicate state from body
    body_start = next(i for i, l in enumerate(lines) if i >= start and "function formatTimestampIST" in l)
    body = "".join(lines[body_start:end])

    for name in EXPORT_FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    body = re.sub(r"\bcurrentExperience\b", "getCurrentExperience()", body)
    body = re.sub(r"\bactiveBusinessWorkspace\b", "getActiveBusinessWorkspace()", body)
    body = re.sub(r"\bdashboardPreview\b", "getDashboardPreview()", body)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    # Remove from banner through before GRUHAMITRA header
    gruha = next(i for i, l in enumerate(lines) if "SECTION: GRUHAMITRA WORKSPACE" in l)
    gruha_header = gruha
    while gruha_header > 0 and lines[gruha_header - 1].strip().startswith("// ═"):
        gruha_header -= 1

    text = "".join(lines[:start] + lines[gruha_header:])
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js {start + 1}-{gruha_header}")


if __name__ == "__main__":
    main()
