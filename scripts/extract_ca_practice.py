#!/usr/bin/env python3
"""Extract CA practice state + loaders into modules/workspaces/ca-practice.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/ca-practice.js"

HEADER = '''\
// ====================================================================
// SECTION: CA PRACTICE — state + loaders
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCaPractice(...).
// CA renderers remain in app.js for a later seam.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastCaDocuments = [];
export let lastCaDocumentsResult = null;
export let lastCaClients = [];
export let lastCaClientsResult = null;
export let caAccessUsers = [];
export let caAccessLoading = false;
export let caInviteError = "";
export let caInviteSuccess = "";
export let caClientDraft = {
  client_name: "",
  gstin: "",
  pan: "",
  contact_person: "",
  assigned_to: "",
  client_owner: "",
  engagement_type: "",
  access_level: "view_only",
  compliance_tracks: "",
  notes: "",
};
export let caPracticeFilters = {
  status: "",
  client_name: "",
  assigned_to: "",
  priority: "",
};
export let caDocumentAttachmentState = {
  document_id: "",
  client_name: "",
  items: [],
  loading: false,
};

export const CA_DOCUMENT_WORKFLOW = ["uploaded", "under_review", "query_raised", "reviewed", "posted"];
export const CA_DOCUMENT_LABELS = {
  uploaded: "Uploaded",
  under_review: "Under review",
  query_raised: "Query raised",
  reviewed: "Reviewed",
  posted: "Posted",
};
export const CA_DOCUMENT_PRIORITY_LABELS = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCaPractice(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCaPractice() must be called before using CA practice helpers");
  }
  return deps;
}

function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }

export function setCaInviteError(value) { caInviteError = value; }
export function setCaInviteSuccess(value) { caInviteSuccess = value; }
export function setCaClientDraft(value) { caClientDraft = value; }
export function setCaPracticeFilters(value) { caPracticeFilters = value; }
export function setCaDocumentAttachmentState(value) { caDocumentAttachmentState = value; }
export function setCaAccessLoading(value) { caAccessLoading = !!value; }
export function setCaAccessUsers(value) { caAccessUsers = Array.isArray(value) ? value : []; }
export function resetCaPracticeWorkspaceState() {
  lastCaDocuments = [];
  lastCaDocumentsResult = null;
  lastCaClients = [];
  lastCaClientsResult = null;
  caAccessUsers = [];
  caInviteError = "";
  caInviteSuccess = "";
}

'''

EXPORT_FUNCS = [
    "loadCaPracticeDocuments",
    "loadCaClients",
    "rerenderCaPracticeIfActive",
    "loadCaAccessUsers",
    "createCaPracticeDocument",
    "createCaClient",
    "loadCaDocumentAttachments",
    "updateCaPracticeDocumentStatus",
]


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


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    sigs = [
        "async function loadCaPracticeDocuments",
        "async function loadCaClients",
        "function rerenderCaPracticeIfActive",
        "async function loadCaAccessUsers",
        "async function createCaPracticeDocument",
        "async function createCaClient",
        "async function loadCaDocumentAttachments",
        "async function updateCaPracticeDocumentStatus",
    ]
    blocks = [find_fn_block(lines, s) for s in sigs]

    body = "\n".join("".join(lines[s:e]) for s, e in blocks)
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

    for start, end in sorted(blocks, key=lambda t: t[0], reverse=True):
        del lines[start:end]

    text = "".join(lines)

    # Remove moved state + constants (order matters: longer blocks first)
    patterns = [
        r"(?ms)^let caDocumentAttachmentState = \{.*?\};\n",
        r"(?ms)^let caPracticeFilters = \{.*?\};\n",
        r"(?ms)^let caClientDraft = \{.*?\};\n",
        r"(?m)^let caInviteSuccess = \"\";\n",
        r"(?m)^let caInviteError = \"\";\n",
        r"(?m)^let caAccessLoading = false;\n",
        r"(?m)^let caAccessUsers = \[\];\n",
        r"(?m)^let lastCaClientsResult = null;\n",
        r"(?m)^let lastCaClients = \[\];\n",
        r"(?m)^let lastCaDocumentsResult = null;\n",
        r"(?m)^let lastCaDocuments = \[\];\n",
        r"(?ms)^const CA_DOCUMENT_PRIORITY_LABELS = \{.*?\};\n",
        r"(?ms)^const CA_DOCUMENT_LABELS = \{.*?\};\n",
        r"(?m)^const CA_DOCUMENT_WORKFLOW = \[.*?\];\n",
    ]
    for pat in patterns:
        text, n = re.subn(pat, "", text, count=1)
        if n != 1:
            raise SystemExit(f"failed to remove pattern {pat!r} n={n}")

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
