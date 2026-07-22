"""One-shot extractor: HR workspace from mitrabooks-erp/app.js -> modules/workspaces/hr.js"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "hr.js"

UI_REPLACEMENTS = [
    ("hrTab", "hrUi.tab"),
    ("hrShowAddEmployee", "hrUi.showAddEmployee"),
    ("hrAssignFor", "hrUi.assignFor"),
    ("hrShowLetterSettings", "hrUi.showLetterSettings"),
    ("hrSelectedRunId", "hrUi.selectedRunId"),
    ("hrRunSlips", "hrUi.runSlips"),
    ("hrError", "hrUi.error"),
]

EXPORT_NAMES = [
    "loadHrWorkspace",
    "renderHrWorkspace",
    "loadHrLeave",
    "loadHrTax",
    "loadHrFnf",
    "loadHrRunSlips",
    "hrEnable",
    "hrCreateEmployee",
    "hrCreateStructure",
    "hrAssignSalary",
    "hrDownloadLetter",
    "hrDownloadJoiningLetter",
    "hrMarkJoined",
    "hrMarkDeclined",
    "hrSaveLetterSettings",
    "hrRunPayroll",
    "hrDownloadSlipPdf",
    "hrCreateLeaveType",
    "hrAllocateLeave",
    "hrApplyLeave",
    "hrDecideLeave",
    "hrCreateDeclaration",
    "hrVerifyDeclaration",
    "hrCreateFnf",
    "hrTransitionFnf",
    "hrDownloadFnfPdf",
]

HEADER = '''// ====================================================================
// SECTION: HR / PAYROLL ADD-ON WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initHrWorkspace(...).
// ====================================================================

import { apiRequest, downloadApiFile } from "../../../shared/api-client.js";

export const hrUi = {
  tab: "employees",
  showAddEmployee: false,
  assignFor: "",
  showLetterSettings: false,
  selectedRunId: "",
  runSlips: [],
  error: "",
};

let hrAccess = null;
let hrEmployees = [];
let hrRuns = [];
let hrAnalytics = null;
let hrLeaveTypes = [];
let hrLeaveApplications = [];
let hrDeclarations = [];
let hrFnf = [];
let hrStructures = [];
let hrAppointmentConfig = null;

/** @type {{ escapeHtml: (v: string) => string, refreshHrView: () => void } | null} */
let deps = null;

export function initHrWorkspace({ escapeHtml, refreshHrView }) {
  deps = { escapeHtml, refreshHrView };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initHrWorkspace() must be called before using the HR workspace");
  }
  return deps;
}

function refreshHrView() {
  if (deps) {
    deps.refreshHrView();
  }
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

'''

OLD_REFRESH = """function refreshHrView() {
  if (currentExperience === \"mitrabooks\" && activeBusinessWorkspace === \"hr\") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

"""


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    # 1-based line numbers from app.js: 5847-6604
    hr_body = "".join(lines[5846:6604])
    hr_body = hr_body.replace(OLD_REFRESH, "")
    for old, new in UI_REPLACEMENTS:
        hr_body = re.sub(rf"\b{old}\b", new, hr_body)
    for name in EXPORT_NAMES:
        hr_body = hr_body.replace(f"async function {name}", f"export async function {name}")
        hr_body = hr_body.replace(f"function {name}", f"export function {name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + hr_body, encoding="utf-8")
    print(f"Wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
