#!/usr/bin/env python3
"""Wire ca-practice module into app.js; bump cache v69→v70; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

IMPORT = '''\
import {
  initCaPractice,
  lastCaDocuments,
  lastCaDocumentsResult,
  lastCaClients,
  lastCaClientsResult,
  caAccessUsers,
  caAccessLoading,
  caInviteError,
  caInviteSuccess,
  caClientDraft,
  caPracticeFilters,
  caDocumentAttachmentState,
  CA_DOCUMENT_WORKFLOW,
  CA_DOCUMENT_LABELS,
  CA_DOCUMENT_PRIORITY_LABELS,
  setCaInviteError,
  setCaInviteSuccess,
  setCaClientDraft,
  setCaPracticeFilters,
  setCaDocumentAttachmentState,
  resetCaPracticeWorkspaceState,
  loadCaPracticeDocuments,
  loadCaClients,
  rerenderCaPracticeIfActive,
  loadCaAccessUsers,
  createCaPracticeDocument,
  createCaClient,
  loadCaDocumentAttachments,
  updateCaPracticeDocumentStatus,
} from "./modules/workspaces/ca-practice.js";
'''

INIT = '''\
// Wire CA practice loaders (avoids import cycle with app.js)
initCaPractice({
  setLoginStatus,
  statusDetailText,
  getApiOutput: () => apiOutput,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  listBusinessAttachments,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/ca-practice.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/coa.js";\n'
    if marker not in app:
        raise SystemExit("coa import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    replacements = [
        (
            "get caClientDraft() { return caClientDraft; },\n  set caClientDraft(v) { caClientDraft = v; },",
            "get caClientDraft() { return caClientDraft; },\n  set caClientDraft(v) { setCaClientDraft(v); },",
        ),
        (
            "get caPracticeFilters() { return caPracticeFilters; },\n  set caPracticeFilters(v) { caPracticeFilters = v; },",
            "get caPracticeFilters() { return caPracticeFilters; },\n  set caPracticeFilters(v) { setCaPracticeFilters(v); },",
        ),
    ]
    # invite error/success may use direct assignment via deps
    for old, new in replacements:
        if old not in app:
            raise SystemExit(f"binding not found:\n{old}")
        app = app.replace(old, new, 1)

    # caInviteError / caInviteSuccess setters if present as get/set
    app = app.replace(
        "set caInviteError(v) { caInviteError = v; }",
        "set caInviteError(v) { setCaInviteError(v); }",
    )
    app = app.replace(
        "set caInviteSuccess(v) { caInviteSuccess = v; }",
        "set caInviteSuccess(v) { setCaInviteSuccess(v); }",
    )

    idx = app.find("initCoa({")
    if idx < 0:
        raise SystemExit("initCoa not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v69",
        "app.js?v=mitrabooks-erp-v70",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wired ca-practice; cache v70; app.js baseline={app_lines}")


if __name__ == "__main__":
    main()
