#!/usr/bin/env python3
"""Wire manufacturing module into app.js; bump cache v64→v65; update baseline."""
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
  initManufacturing,
  mfgAccess,
  mfgTab,
  mfgError,
  mfgBudgetVsActual,
  mfgCompleteFor,
  mfgPl,
  mfgPlFrom,
  mfgPlTo,
  mfgWoActualDraft,
  setMfgTab,
  setMfgError,
  setMfgBudgetVsActual,
  setMfgCompleteFor,
  setMfgPlFrom,
  setMfgPlTo,
  setMfgWoActualDraft,
  loadMfgWorkspace,
  loadMfgPl,
  mfgEnableLayer,
  mfgCreateCostCentre,
  mfgCreateBudget,
  mfgSetBudgetStatus,
  mfgViewBudgetVsActual,
  mfgAddBomComponent,
  mfgRemoveBomComponent,
  mfgCreateBom,
  mfgCreateWorkOrder,
  mfgSetWorkOrderStatus,
  mfgOpenComplete,
  mfgAddWoActual,
  mfgRemoveWoActual,
  mfgCompleteWorkOrder,
  renderManufacturingWorkspace,
} from "./modules/workspaces/manufacturing.js";
'''

INIT = '''\
// Wire manufacturing workspace (avoids import cycle with app.js)
initManufacturing({
  escapeHtml,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  refreshMfgView: () => {
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "manufacturing") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  },
});
'''

REFRESH_STUB = '''\
function refreshMfgView() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "manufacturing") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/manufacturing.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/financial-reports.js";\n'
    if marker not in app:
        raise SystemExit("financial-reports import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # Replace direct mfgTab/mfgError assignments in setBusinessWorkspace
    app, n1 = re.subn(
        r'(\} else if \(workspace === "manufacturing"\) \{\n)\s*mfgTab = "cost-centres";\n\s*mfgError = "";\n',
        r'\1    setMfgTab("cost-centres");\n    setMfgError("");\n',
        app,
        count=1,
    )
    if n1 != 1:
        raise SystemExit(f"setBusinessWorkspace mfg assign rewrite failed n={n1}")

    # Update events deps getters/setters to use module setters
    replacements = [
        (
            "get mfgBudgetVsActual() { return mfgBudgetVsActual; },\n  set mfgBudgetVsActual(v) { mfgBudgetVsActual = v; },",
            "get mfgBudgetVsActual() { return mfgBudgetVsActual; },\n  set mfgBudgetVsActual(v) { setMfgBudgetVsActual(v); },",
        ),
        (
            "get mfgCompleteFor() { return mfgCompleteFor; },\n  set mfgCompleteFor(v) { mfgCompleteFor = v; },",
            "get mfgCompleteFor() { return mfgCompleteFor; },\n  set mfgCompleteFor(v) { setMfgCompleteFor(v); },",
        ),
        (
            "get mfgError() { return mfgError; },\n  set mfgError(v) { mfgError = v; },",
            "get mfgError() { return mfgError; },\n  set mfgError(v) { setMfgError(v); },",
        ),
        (
            "get mfgPlFrom() { return mfgPlFrom; },\n  set mfgPlFrom(v) { mfgPlFrom = v; },",
            "get mfgPlFrom() { return mfgPlFrom; },\n  set mfgPlFrom(v) { setMfgPlFrom(v); },",
        ),
        (
            "get mfgPlTo() { return mfgPlTo; },\n  set mfgPlTo(v) { mfgPlTo = v; },",
            "get mfgPlTo() { return mfgPlTo; },\n  set mfgPlTo(v) { setMfgPlTo(v); },",
        ),
        (
            "get mfgTab() { return mfgTab; },\n  set mfgTab(v) { mfgTab = v; },",
            "get mfgTab() { return mfgTab; },\n  set mfgTab(v) { setMfgTab(v); },",
        ),
        (
            "get mfgWoActualDraft() { return mfgWoActualDraft; },\n  set mfgWoActualDraft(v) { mfgWoActualDraft = v; },",
            "get mfgWoActualDraft() { return mfgWoActualDraft; },\n  set mfgWoActualDraft(v) { setMfgWoActualDraft(v); },",
        ),
    ]
    for old, new in replacements:
        if old not in app:
            raise SystemExit(f"events binding not found:\n{old}")
        app = app.replace(old, new, 1)

    idx = app.find("initFinancialReports({")
    if idx < 0:
        raise SystemExit("initFinancialReports not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initFinancialReports close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v64",
        "app.js?v=mitrabooks-erp-v65",
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
    print(f"Wired manufacturing; cache v65; app.js baseline={app_lines}")


if __name__ == "__main__":
    main()
