#!/usr/bin/env python3
"""Wire mandir-create-forms into app.js; bump cache v86→v87; update baseline."""
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
  initMandirCreateForms,
  renderBankAccountOptions,
  mandirAccountOptionValue,
  mandirAccountOptionLabel,
  renderMandirAccountOptions,
  mandirPaymentAccountOptions,
  mandirExpenseAccountOptions,
  renderMandirCreateForms,
  openMandirVerificationDialog,
  mandirReceiptFromVerifyPayload,
  submitMandirPublicPaymentVerification,
  openMandirRejectionDialog,
  submitMandirPublicPaymentRejection,
  openMandirCorrectionDialog,
  submitMandirPublicPaymentCorrection,
  downloadMandirReceipt,
  closeReceiptPreview,
  previewMandirReceipt,
  openMandirCancelReceiptDialog,
  submitMandirCancelReceipt,
  compactOptionalPhone,
  formNumber,
  formText,
  setMandirFormResult,
  mandirReceiptFromCreatePayload,
  submitMandirDonationForm,
  submitMandirComplianceForm,
  submitMandirSevaForm,
  submitMandirExpenseForm,
  submitMandirCreateForm,
  readMandirListFilterValues,
  applyMandirListFilter,
  resetMandirListFilter,
  pageMandirList,
  setMandirWorkspace,
} from "./modules/workspaces/mandir-create-forms.js";
'''

INIT = '''\
// Wire Mandir create forms + posting dialogs (avoids import cycle with app.js)
initMandirCreateForms({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  apiRequest,
  renderJson,
  loadMandirDashboard,
  downloadApiFile,
  fetchApiFileObjectUrl,
  syncMandirNavActiveState,
  getLastMandirPaymentAccounts: () => lastMandirPaymentAccounts,
  getLastMandirAccounts: () => lastMandirAccounts,
  getLastMandirFormResult: () => lastMandirFormResult,
  setLastMandirFormResult: (value) => { lastMandirFormResult = value; },
  getLastMandirReceipt: () => lastMandirReceipt,
  setLastMandirReceipt: (value) => { lastMandirReceipt = value; },
  setLastMandirComplianceConfig: (value) => { lastMandirComplianceConfig = value; },
  getMandirReportState: () => mandirReportState,
  getMandirListState: () => mandirListState,
  getMandirListPageSize: () => MANDIR_LIST_PAGE_SIZE,
  setActiveMandirWorkspace: (view) => { activeMandirWorkspace = view; },
  getActiveReceiptPreviewObjectUrl: () => activeReceiptPreviewObjectUrl,
  setActiveReceiptPreviewObjectUrl: (value) => { activeReceiptPreviewObjectUrl = value; },
  mandirVerificationDialog,
  mandirVerificationPaymentId,
  mandirVerificationLabel,
  mandirVerificationUtr,
  mandirVerificationDate,
  mandirVerificationBankAccount,
  mandirRejectionDialog,
  mandirRejectionPaymentId,
  mandirRejectionLabel,
  mandirRejectionReason,
  mandirCorrectionDialog,
  mandirCorrectionForm,
  mandirCorrectionPaymentId,
  mandirCorrectionLabel,
  mandirCorrectionAmount,
  mandirCorrectionPhone,
  mandirCorrectionType,
  mandirCorrectionPurpose,
  mandirCancelReceiptDialog,
  mandirCancelReceiptUrl,
  mandirCancelReceiptLabel,
  mandirCancelReceiptReason,
  mandirCancelRefundMode,
  mandirCancelRefundReference,
  mandirCancelReceiptSubmit,
  receiptPreviewDialog,
  receiptPreviewFrame,
  receiptPreviewLabel,
  dashboardPreview,
  apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/mandir-create-forms.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/mandir-dashboard.js";\n'
    if marker not in app:
        raise SystemExit("mandir-dashboard import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initMandirDashboard({")
    if idx < 0:
        raise SystemExit("initMandirDashboard not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v86",
        "app.js?v=mitrabooks-erp-v87",
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
    print(f"Wired mandir-create-forms; app.js={app_lines}; cache=v87")


if __name__ == "__main__":
    main()
