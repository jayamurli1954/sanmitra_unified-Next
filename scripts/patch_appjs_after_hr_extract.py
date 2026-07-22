"""Patch app.js after HR workspace extraction."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"

IMPORT_BLOCK = '''import {
  initHrWorkspace,
  hrUi,
  loadHrWorkspace,
  renderHrWorkspace,
  loadHrLeave,
  loadHrTax,
  loadHrFnf,
  loadHrRunSlips,
  hrEnable,
  hrCreateEmployee,
  hrCreateStructure,
  hrAssignSalary,
  hrDownloadLetter,
  hrDownloadJoiningLetter,
  hrMarkJoined,
  hrMarkDeclined,
  hrSaveLetterSettings,
  hrRunPayroll,
  hrDownloadSlipPdf,
  hrCreateLeaveType,
  hrAllocateLeave,
  hrApplyLeave,
  hrDecideLeave,
  hrCreateDeclaration,
  hrVerifyDeclaration,
  hrCreateFnf,
  hrTransitionFnf,
  hrDownloadFnfPdf,
} from "./modules/workspaces/hr.js";
'''

INIT_BLOCK = '''
// Wire HR workspace deps (avoids modules/workspaces/hr.js importing app.js)
initHrWorkspace({
  escapeHtml,
  refreshHrView: () => {
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "hr") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  },
});
'''

REPLACEMENTS = [
    ("hrTab = ", "hrUi.tab = "),
    ("hrShowAddEmployee = ", "hrUi.showAddEmployee = "),
    ("hrAssignFor = ", "hrUi.assignFor = "),
    ("hrShowLetterSettings = ", "hrUi.showLetterSettings = "),
    ("hrSelectedRunId = ", "hrUi.selectedRunId = "),
    ("hrRunSlips = ", "hrUi.runSlips = "),
    ("hrError = ", "hrUi.error = "),
]


def line_is_hr_state_start(line: str) -> bool:
    return line.startswith("// ── HR / Payroll add-on workspace state")


def line_is_hr_section_start(line: str) -> bool:
    return "SECTION: HR / PAYROLL ADD-ON WORKSPACE" in line


def line_is_mfg_section_start(line: str) -> bool:
    return "MANUFACTURING & COST-CENTRE ADD-ON" in line


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Remove HR state block (comment + lets through hrShowLetterSettings)
    out: list[str] = []
    skip = False
    for line in lines:
        if line_is_hr_state_start(line):
            skip = True
            continue
        if skip:
            if line.startswith("const MITRABOOKS_SETTINGS_GROUPS"):
                skip = False
                out.append(line)
            continue
        out.append(line)
    lines = out

    # Remove HR section (from HR section banner through line before mfg banner)
    out = []
    skip = False
    for i, line in enumerate(lines):
        if line_is_hr_section_start(line):
            skip = True
            continue
        if skip and line_is_mfg_section_start(line):
            skip = False
            if i > 0 and lines[i - 1].strip().startswith("// ═"):
                out.append(lines[i - 1])
            out.append(line)
            continue
        if skip:
            continue
        if "SECTION: HR / PAYROLL" in line:
            continue
        out.append(line)
    lines = out

    text = "".join(lines)

    if 'from "./modules/workspaces/hr.js"' not in text:
        text = text.replace(
            '} from "./modules/widgets.js";\n',
            '} from "./modules/widgets.js";\n' + IMPORT_BLOCK,
        )

    if "initHrWorkspace({" not in text:
        text = text.replace(
            "renderExecutiveDashboard: () => renderBusinessExecutiveDashboard(),\n});\n",
            "renderExecutiveDashboard: () => renderBusinessExecutiveDashboard(),\n});"
            + INIT_BLOCK,
        )

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    APP.write_text(text, encoding="utf-8")
    print(f"Patched {APP} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
