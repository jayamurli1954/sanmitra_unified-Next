// ====================================================================
// SECTION: EVENT HANDLERS — click / change / input / keydown
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: listener bodies unchanged aside from deps.<binding> for shell
// bindings (keeps mutable let assignment semantics). Wire via initEventHandlers.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initEventHandlers(injected) {
  deps = injected;
  installEventHandlers();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initEventHandlers() must be called before registering handlers");
  }
  return deps;
}

function installEventHandlers() {
  const deps = requireDeps();

  // SECTION: EVENT HANDLERS — click / change / input / keydown
  // NOTE  : Single delegated listener on dashboardPreview for all workspace actions
  // ══════════════════════════════════════════════════════════════════════

  deps.nav.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-platform-workspace]");
    if (!link) {
      return;
    }
    event.preventDefault();
    if (link.getAttribute("aria-disabled") === "true") {
      return;
    }
    deps.setPlatformWorkspace(link.dataset.platformWorkspace || "dashboard");
  });

  deps.dashboardPreview.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-platform-action], [data-mandir-action], [data-gruha-action], [data-accounting-action], [data-business-action], [data-coa-action]");
    if (!button) {
      return;
    }
    const requestId = button.getAttribute("data-request-id") || "";
    const action = button.getAttribute("data-platform-action");
    const mandirAction = button.getAttribute("data-mandir-action");
    const gruhaAction = button.getAttribute("data-gruha-action");
    const accountingAction = button.getAttribute("data-accounting-action");
    const businessAction = button.getAttribute("data-business-action");
    if (action === "approve") {
      deps.approveOnboardingRequest(requestId);
    } else if (action === "reject") {
      deps.rejectOnboardingRequest(requestId);
    } else if (action === "entitlements") {
      deps.openTenantEntitlementsDialog(button);
    } else if (action === "open-platform-owner") {
      deps.setExperience("platform");
    } else if (mandirAction === "verify-public-payment") {
      deps.openMandirVerificationDialog(button);
    } else if (mandirAction === "reject-public-payment") {
      deps.openMandirRejectionDialog(button);
    } else if (mandirAction === "correct-public-payment") {
      deps.openMandirCorrectionDialog(button);
    } else if (mandirAction === "download-receipt") {
      deps.downloadMandirReceipt(button);
    } else if (mandirAction === "preview-receipt") {
      deps.previewMandirReceipt(button);
    } else if (mandirAction === "cancel-receipt") {
      deps.openMandirCancelReceiptDialog(button);
    } else if (mandirAction === "apply-list-filter") {
      deps.applyMandirListFilter(button.getAttribute("data-list-kind") || "");
    } else if (mandirAction === "reset-list-filter") {
      deps.resetMandirListFilter(button.getAttribute("data-list-kind") || "");
    } else if (mandirAction === "page-list") {
      deps.pageMandirList(button.getAttribute("data-list-kind") || "", button.getAttribute("data-page-direction") || "next");
    } else if (mandirAction === "workspace-view") {
      deps.setMandirWorkspace(button.getAttribute("data-workspace-view") || "overview");
    } else if (gruhaAction === "workspace-view") {
      deps.setGruhaWorkspace(button.getAttribute("data-workspace-view") || "overview");
    } else if (accountingAction === "apply-drilldown") {
      deps.applyAccountingDrilldownFilters();
    } else if (accountingAction === "reset-drilldown") {
      deps.resetAccountingDrilldown();
    } else if (accountingAction === "drill") {
      deps.drillAccountingReport(button);
    } else if (accountingAction === "voucher-detail") {
      deps.openAccountingVoucherDetail(button);
    } else if (accountingAction === "tb-ledger") {
      deps.openMandirTrialBalanceLedger(button);
    } else if (businessAction === "open-create-party") {
      deps.openBusinessCreatePartyDialog();
    } else if (businessAction === "edit-party") {
      deps.openBusinessEditPartyDialog(button);
    } else if (businessAction === "deactivate-party") {
      const partyId = button.getAttribute("data-party-id") || "";
      if (confirm("Deactivate this party? It will no longer appear in new vouchers.")) {
        deps.deactivateBusinessParty(partyId);
      }
    } else if (businessAction === "apply-list-filter") {
      deps.applyBusinessListFilter(button.getAttribute("data-list-kind") || "");
    } else if (businessAction === "reset-list-filter") {
      deps.resetBusinessListFilter(button.getAttribute("data-list-kind") || "");
    } else if (businessAction === "page-list") {
      deps.pageBusinessList(button.getAttribute("data-list-kind") || "", button.getAttribute("data-page-direction") || "next");
    } else if (businessAction === "voucher-queue-refresh") {
      deps.loadVoucherApprovalQueue(true, { surfaceErrors: true });
    } else if (businessAction === "workspace-view") {
      deps.setBusinessWorkspace(button.getAttribute("data-workspace-view") || "overview");
    } else if (businessAction === "settings-detail") {
      deps.activeSettingsDetailId = button.getAttribute("data-settings-id") || "";
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "settings-back") {
      deps.activeSettingsDetailId = "";
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "save-settings-section") {
      deps.saveBusinessAdminSettingsSection(button.getAttribute("data-settings-section") || "");
    } else if (businessAction === "ca-client-filter") {
      deps.caPracticeFilters = { ...deps.caPracticeFilters, client_name: button.getAttribute("data-client-name") || "" };
      deps.loadCaPracticeDocuments();
    } else if (businessAction === "ca-client-filter-clear") {
      deps.caPracticeFilters = { ...deps.caPracticeFilters, client_name: "" };
      deps.loadCaPracticeDocuments();
    } else if (businessAction === "ca-client-refresh") {
      deps.loadCaClients();
    } else if (businessAction === "hr-refresh") {
      deps.loadHrWorkspace();
    } else if (businessAction === "hr-enable") {
      deps.hrEnable();
    } else if (businessAction === "hr-add-employee-toggle") {
      deps.hrUi.showAddEmployee = true; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-add-employee-cancel") {
      deps.hrUi.showAddEmployee = false; deps.hrUi.error = ""; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-create-employee") {
      deps.hrCreateEmployee();
    } else if (businessAction === "hr-create-structure") {
      deps.hrCreateStructure();
    } else if (businessAction === "hr-assign-open") {
      deps.hrUi.assignFor = button.getAttribute("data-emp-id") || ""; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-assign-cancel") {
      deps.hrUi.assignFor = ""; deps.hrUi.error = ""; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-assign-submit") {
      deps.hrAssignSalary();
    } else if (businessAction === "hr-letter") {
      deps.hrDownloadLetter(button);
    } else if (businessAction === "hr-joining-letter") {
      deps.hrDownloadJoiningLetter(button);
    } else if (businessAction === "hr-mark-joined") {
      deps.hrMarkJoined(button);
    } else if (businessAction === "hr-mark-declined") {
      deps.hrMarkDeclined(button);
    } else if (businessAction === "hr-letter-settings-toggle") {
      deps.hrUi.showLetterSettings = true; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-letter-settings-cancel") {
      deps.hrUi.showLetterSettings = false; deps.hrUi.error = ""; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "hr-save-letter-settings") {
      deps.hrSaveLetterSettings();
    } else if (businessAction === "hr-tab") {
      deps.hrUi.tab = button.getAttribute("data-hr-tab") || "employees";
      if (deps.hrUi.tab !== "payroll") { deps.hrUi.selectedRunId = ""; deps.hrUi.runSlips = []; }
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
      if (deps.hrUi.tab === "leave") deps.loadHrLeave();
      else if (deps.hrUi.tab === "tax") deps.loadHrTax();
      else if (deps.hrUi.tab === "fnf") deps.loadHrFnf();
    } else if (businessAction === "hr-run-payroll") {
      deps.hrRunPayroll();
    } else if (businessAction === "hr-view-slips") {
      deps.loadHrRunSlips(button.getAttribute("data-run-id") || "");
    } else if (businessAction === "hr-slip-pdf") {
      deps.hrDownloadSlipPdf(button);
    } else if (businessAction === "hr-create-leave-type") {
      deps.hrCreateLeaveType();
    } else if (businessAction === "hr-allocate-leave") {
      deps.hrAllocateLeave();
    } else if (businessAction === "hr-apply-leave") {
      deps.hrApplyLeave();
    } else if (businessAction === "hr-approve-leave") {
      deps.hrDecideLeave(button, "approve");
    } else if (businessAction === "hr-reject-leave") {
      deps.hrDecideLeave(button, "reject");
    } else if (businessAction === "hr-create-declaration") {
      deps.hrCreateDeclaration();
    } else if (businessAction === "hr-approve-decl") {
      deps.hrVerifyDeclaration(button, true);
    } else if (businessAction === "hr-reject-decl") {
      deps.hrVerifyDeclaration(button, false);
    } else if (businessAction === "hr-create-fnf") {
      deps.hrCreateFnf();
    } else if (businessAction === "hr-fnf-approve") {
      deps.hrTransitionFnf(button, "approve");
    } else if (businessAction === "hr-fnf-pay") {
      deps.hrTransitionFnf(button, "pay");
    } else if (businessAction === "hr-fnf-pdf") {
      deps.hrDownloadFnfPdf(button);
    } else if (businessAction === "mfg-refresh") {
      deps.loadMfgWorkspace();
    } else if (businessAction === "mfg-tab") {
      deps.mfgTab = button.getAttribute("data-mfg-tab") || "cost-centres";
      deps.mfgBudgetVsActual = null;
      deps.mfgCompleteFor = "";
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
      if (deps.mfgTab === "pl" && !deps.mfgPl) deps.loadMfgPl();
    } else if (businessAction === "mfg-enable-cost-centre") {
      deps.mfgEnableLayer("cost-centre");
    } else if (businessAction === "mfg-enable-manufacturing") {
      deps.mfgEnableLayer("manufacturing");
    } else if (businessAction === "mfg-create-cc") {
      deps.mfgCreateCostCentre();
    } else if (businessAction === "mfg-create-budget") {
      deps.mfgCreateBudget();
    } else if (businessAction === "mfg-budget-status") {
      deps.mfgSetBudgetStatus(button);
    } else if (businessAction === "mfg-budget-vs-actual") {
      deps.mfgViewBudgetVsActual(button);
    } else if (businessAction === "mfg-pl-run") {
      deps.mfgPlFrom = document.getElementById("mfg-pl-from")?.value || "";
      deps.mfgPlTo = document.getElementById("mfg-pl-to")?.value || "";
      deps.loadMfgPl();
    } else if (businessAction === "mfg-pl-export") {
      const fmt = button.getAttribute("data-format") || "csv";
      const qs = [`format=${encodeURIComponent(fmt)}`];
      if (deps.mfgPlFrom) qs.push("from_date=" + encodeURIComponent(deps.mfgPlFrom));
      if (deps.mfgPlTo) qs.push("to_date=" + encodeURIComponent(deps.mfgPlTo));
      deps.downloadApiFile("mitrabooks", "/api/v1/business/mfg/cost-centre/pl/export?" + qs.join("&"), `cost_centre_pl.${fmt}`);
    } else if (businessAction === "mfg-bom-add-comp") {
      deps.mfgAddBomComponent();
    } else if (businessAction === "mfg-bom-remove-comp") {
      deps.mfgRemoveBomComponent(button);
    } else if (businessAction === "mfg-create-bom") {
      deps.mfgCreateBom();
    } else if (businessAction === "mfg-create-wo") {
      deps.mfgCreateWorkOrder();
    } else if (businessAction === "mfg-wo-status") {
      deps.mfgSetWorkOrderStatus(button);
    } else if (businessAction === "mfg-wo-open-complete") {
      deps.mfgOpenComplete(button);
    } else if (businessAction === "mfg-wo-complete-cancel") {
      deps.mfgCompleteFor = ""; deps.mfgWoActualDraft = []; deps.mfgError = ""; deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (businessAction === "mfg-wo-add-actual") {
      deps.mfgAddWoActual();
    } else if (businessAction === "mfg-wo-remove-actual") {
      deps.mfgRemoveWoActual(button);
    } else if (businessAction === "mfg-wo-complete") {
      deps.mfgCompleteWorkOrder();
    } else if (businessAction === "open-create-voucher") {
      deps.openBusinessCreateVoucherDialog();
    } else if (businessAction === "remove-voucher-line") {
      deps.removeVoucherLine(button.getAttribute("data-line-id") || "");
    } else if (businessAction === "reverse-voucher") {
      const voucherId = button.getAttribute("data-voucher-id") || "";
      if (confirm("Reverse this voucher? A reversal entry will be created.")) {
        deps.reverseBusinessVoucher(voucherId);
      }
    } else if (businessAction === "review-voucher-approve") {
      const voucherId = button.getAttribute("data-voucher-id") || "";
      deps.reviewBusinessVoucher(voucherId, true, "Approved from voucher queue");
    } else if (businessAction === "review-voucher-reject") {
      const voucherId = button.getAttribute("data-voucher-id") || "";
      const rejectionReason = prompt("Enter rejection reason for this voucher:", "Needs correction") || "";
      if (rejectionReason) {
        deps.reviewBusinessVoucher(voucherId, false, "Rejected from voucher queue", rejectionReason);
      }
    } else if (businessAction === "view-audit-event") {
      deps.openAuditEventDetailDialog(button.getAttribute("data-event-id") || "");
    } else if (businessAction === "apply-audit-filter") {
      deps.applyAuditFilters();
    } else if (businessAction === "reset-audit-filter") {
      deps.resetAuditFilters();
    } else if (businessAction === "page-audit") {
      deps.pageAuditList(button.getAttribute("data-page-direction") || "next");
    } else if (businessAction === "ca-doc-refresh") {
      deps.loadCaPracticeDocuments();
    } else if (businessAction === "ca-doc-clear-filters") {
      deps.caPracticeFilters = { status: "", client_name: "", assigned_to: "", priority: "" };
      deps.loadCaPracticeDocuments();
    } else if (businessAction === "ca-doc-files") {
      deps.loadCaDocumentAttachments(
        button.getAttribute("data-document-id") || "",
        button.getAttribute("data-client-name") || "",
      );
    } else if (businessAction === "refresh-financial-health") {
      deps.loadFinancialHealth();
    } else if (businessAction === "ca-doc-status") {
      deps.updateCaPracticeDocumentStatus(
        button.getAttribute("data-document-id") || "",
        button.getAttribute("data-status") || "",
      );
    } else if (businessAction === "refresh-attachments") {
      const ownerType = button.getAttribute("data-owner-type") || "";
      const ownerId = button.getAttribute("data-owner-id") || "";
      if (ownerType === "sales_invoice") {
        loadInvoiceAttachments(ownerId);
      } else if (ownerType === "purchase_bill") {
        deps.loadBillAttachments(ownerId);
      } else {
        deps.loadCaDocumentAttachments(ownerId, deps.caDocumentAttachmentState.client_name);
      }
    } else if (businessAction === "upload-attachments") {
      const ownerType = button.getAttribute("data-owner-type") || "";
      const ownerId = button.getAttribute("data-owner-id") || "";
      const panel = button.closest("[data-attachment-panel]");
      const input = panel?.querySelector("[data-attachment-input]");
      const files = Array.from(input?.files || []);
      if (!ownerType || !ownerId) {
        deps.setLoginStatus("warn", "Attachment target missing", "Refresh the document and try again.");
        return;
      }
      if (!files.length) {
        deps.setLoginStatus("warn", "Choose files first", "Select one or more files before uploading.");
        return;
      }
      button.disabled = true;
      const results = await deps.uploadBusinessAttachmentFiles(ownerType, ownerId, files);
      button.disabled = false;
      if (input) {
        input.value = "";
      }
      const successCount = results.filter((item) => item.ok).length;
      const failureCount = results.length - successCount;
      if (ownerType === "sales_invoice") {
        await loadInvoiceAttachments(ownerId);
      } else if (ownerType === "purchase_bill") {
        await deps.loadBillAttachments(ownerId);
      } else {
        await deps.loadCaDocumentAttachments(ownerId, deps.caDocumentAttachmentState.client_name);
      }
      if (failureCount === 0) {
        deps.setLoginStatus("ok", "Attachments uploaded", `${successCount} file(s) uploaded successfully.`);
      } else if (successCount > 0) {
        deps.setLoginStatus("warn", "Attachment upload partially failed", `${successCount} file(s) uploaded and ${failureCount} failed.`);
      } else {
        deps.setLoginStatus("danger", "Attachment upload failed", deps.statusDetailText(results[0]?.payload?.detail) || "No files were uploaded.");
      }
    } else if (businessAction === "download-attachment") {
      const ownerType = button.getAttribute("data-owner-type") || "";
      const ownerId = button.getAttribute("data-owner-id") || "";
      const attachmentId = button.getAttribute("data-attachment-id") || "";
      const fileName = button.getAttribute("data-file-name") || "attachment";
      if (!ownerType || !ownerId || !attachmentId) {
        deps.setLoginStatus("warn", "Attachment missing", "Refresh the document and try the download again.");
        return;
      }
      deps.downloadApiFile("mitrabooks", deps.businessAttachmentPath(ownerType, ownerId, attachmentId), fileName);
    } else if (businessAction === "widget-collapse") {
      deps.toggleWidgetCollapse(button.getAttribute("data-widget-id") || "");
    } else if (businessAction === "open-widget-settings") {
      deps.openWidgetSettings();
    } else if (businessAction === "report-tab") {
      deps.setBusinessReportTab(button.getAttribute("data-report-tab") || "trial-balance");
    } else if (businessAction === "apply-report-filter") {
      deps.applyBusinessReportFilter();
    } else if (businessAction === "aging-kind") {
      deps.setAgingKind(button.getAttribute("data-alloc-kind") || "receivable");
    } else if (businessAction === "alloc-kind") {
      deps.setAllocationKind(button.getAttribute("data-alloc-kind") || "receivable");
    } else if (businessAction === "alloc-select-payment") {
      deps.selectAllocationPayment(button.getAttribute("data-payment-id") || "");
    } else if (businessAction === "alloc-fifo") {
      deps.applyFifoSuggestion();
    } else if (businessAction === "alloc-submit") {
      deps.submitAllocation();
    } else if (businessAction === "export-report") {
      deps.downloadBusinessReport(
        button.getAttribute("data-report-key") || "",
        button.getAttribute("data-report-format") || "csv",
        button.getAttribute("data-report-kind") || "",
      );
    } else if (businessAction === "export-tally-xml") {
      deps.downloadTallyXmlExport();
    } else if (businessAction === "print-report") {
      deps.printBusinessReport();
    } else if (businessAction === "report-ledger") {
      deps.setBusinessReportTab("general-ledger");
      deps.loadBusinessGeneralLedger(button.getAttribute("data-account-id") || "");
    } else if (businessAction === "load-report-ledger") {
      deps.loadBusinessReportLedgerFromSelect();
    } else if (businessAction === "open-create-invoice") {
      deps.openInvoiceCreate();
    } else if (businessAction === "add-invoice-line") {
      deps.addInvoiceLine();
    } else if (businessAction === "remove-invoice-line") {
      deps.removeInvoiceLine(button.getAttribute("data-line-id") || "");
    } else if (businessAction === "save-invoice") {
      deps.submitInvoice();
    } else if (businessAction === "download-invoice-pdf") {
      deps.downloadInvoicePdf(
        button.getAttribute("data-invoice-id") || "",
        button.getAttribute("data-invoice-number") || "",
      );
    } else if (businessAction === "invoice-back") {
      deps.setBusinessSalesView("list");
    } else if (businessAction === "view-invoice") {
      deps.openInvoiceDetail(button.getAttribute("data-invoice-id") || "");
    } else if (businessAction === "begin-reverse-invoice") {
      deps.salesUi.reverseOpen = true;
      deps.rerenderSalesIfActive();
    } else if (businessAction === "cancel-reverse-invoice") {
      deps.salesUi.reverseOpen = false;
      deps.rerenderSalesIfActive();
    } else if (businessAction === "confirm-reverse-invoice") {
      const invoiceId = button.getAttribute("data-invoice-id") || "";
      const dateInput = document.querySelector("[data-reversal-date]");
      deps.cancelInvoice(invoiceId, dateInput?.value || "");
    } else if (businessAction === "open-invoice-settings") {
      deps.openInvoiceSettings();
    } else if (businessAction === "save-invoice-settings") {
      deps.saveInvoiceSettings();
    } else if (businessAction === "open-create-bill") {
      deps.openBillCreate();
    } else if (businessAction === "add-bill-line") {
      deps.addBillLine();
    } else if (businessAction === "remove-bill-line") {
      deps.removeBillLine(button.getAttribute("data-line-id") || "");
    } else if (businessAction === "save-bill") {
      deps.submitBill();
    } else if (businessAction === "bill-back") {
      deps.setBusinessPurchaseView("list");
    } else if (businessAction === "view-bill") {
      deps.openBillDetail(button.getAttribute("data-bill-id") || "");
    } else if (businessAction === "begin-reverse-bill") {
      deps.purchaseUi.reverseOpen = true;
      deps.rerenderPurchaseIfActive();
    } else if (businessAction === "cancel-reverse-bill") {
      deps.purchaseUi.reverseOpen = false;
      deps.rerenderPurchaseIfActive();
    } else if (businessAction === "confirm-reverse-bill") {
      const billId = button.getAttribute("data-bill-id") || "";
      const dateInput = document.querySelector("[data-reversal-date]");
      deps.cancelBill(billId, dateInput?.value || "");
    } else if (businessAction === "lock-period") {
      deps.lockGstPeriodFromInput();
    } else if (businessAction === "unlock-period") {
      deps.setGstPeriodLock(button.getAttribute("data-period") || "", false);
    } else if (businessAction === "gst-preview") {
      deps.previewGstSettlementFromInput();
    } else if (businessAction === "gst-post") {
      deps.postGstSettlement();
    } else if (businessAction === "gstr3b-load") {
      deps.previewGstr3bFromInput();
    } else if (businessAction === "gstr3b-download-json") {
      deps.downloadGstr3bJson();
    } else if (businessAction === "gst-return-type") {
      const rt = button.getAttribute("data-return-type");
      deps.gstReturnState.gstReturnType = ["gstr1", "cmp08", "gstr4", "gstr2b"].includes(rt) ? rt : "gstr3b";
      deps.rerenderBusinessReportsIfActive();
      deps.refreshCurrentBusinessReport();
    } else if (businessAction === "gstr1-load") {
      deps.previewGstr1FromInput();
    } else if (businessAction === "gstr1-download-json") {
      deps.downloadGstr1Json();
    } else if (businessAction === "cmp08-load") {
      deps.previewCmp08FromInput();
    } else if (businessAction === "cmp08-download-json") {
      deps.downloadCmp08Json();
    } else if (businessAction === "cmp08-post") {
      deps.postCmp08Liability();
    } else if (businessAction === "gstr4-load") {
      deps.previewGstr4FromInput();
    } else if (businessAction === "gstr4-download-json") {
      deps.downloadGstr4Json();
    } else if (businessAction === "gstr2b-reconcile") {
      deps.reconcileGstr2b();
    } else if (businessAction === "tds-load") {
      deps.previewTdsRegisterFromInput();
    } else if (businessAction === "bankrecon-load") {
      deps.loadBankReconciliation(document.querySelector("[data-bankrecon-account]")?.value || "");
    } else if (businessAction === "bankrecon-upload") {
      deps.uploadBankStatementFile();
    } else if (businessAction === "bankrecon-match") {
      deps.confirmBankReconMatch(button.getAttribute("data-stmt-id") || "", button.getAttribute("data-line-id") || "");
    } else if (businessAction === "bankrecon-unmatch") {
      deps.reverseBankReconMatch(button.getAttribute("data-match-id") || "");
    } else if (businessAction === "bankrecon-post-voucher") {
      deps.postBankReconStatementVoucher(button.getAttribute("data-stmt-id") || "");
    } else if (businessAction === "stmt-load") {
      deps.loadPartyStatement();
    } else if (businessAction === "dunning-record") {
      deps.recordDunningSent();
    } else if (businessAction === "dunning-copy") {
      deps.copyDunningLetter();
    } else if (businessAction === "ob-template") {
      deps.downloadObTemplate();
    } else if (businessAction === "ob-export") {
      deps.downloadObExport();
    } else if (businessAction === "ob-preview") {
      deps.previewOpeningBalances();
    } else if (businessAction === "ob-post") {
      deps.postOpeningBalances();
    } else if (businessAction === "vi-template") {
      deps.downloadViTemplate();
    } else if (businessAction === "vi-preview") {
      deps.previewBulkVouchers();
    } else if (businessAction === "vi-post") {
      deps.postBulkVouchers();
    } else if (businessAction === "ye-preview") {
      deps.previewYearEnd();
    } else if (businessAction === "ye-post") {
      deps.postYearEndClose();
    } else if (businessAction === "fa-toggle-form") {
      deps.faFormOpen = !deps.faFormOpen;
      deps.rerenderBusinessReportsIfActive();
    } else if (businessAction === "fa-create") {
      deps.createFixedAssetFromForm();
    } else if (businessAction === "fa-dispose") {
      deps.disposeFixedAsset(button.getAttribute("data-asset-id") || "", button);
    } else if (businessAction === "dep-preview") {
      deps.previewDepreciation();
    } else if (businessAction === "dep-post") {
      deps.postDepreciationRun();
    } else if (businessAction === "dim-create") {
      deps.createDimensionFromForm();
    } else if (businessAction === "dim-deactivate") {
      deps.deactivateDimension(button.getAttribute("data-dimension-id") || "");
    } else if (businessAction === "dim-report-load") {
      deps.loadDimensionReport();
      deps.loadBranchConsolidatedReport();
    } else if (businessAction === "dim-report-export") {
      deps.downloadDimensionReport(button.getAttribute("data-format") || "csv");
    } else if (businessAction === "einv-download") {
      deps.downloadInv01Json();
    } else if (businessAction === "einv-record") {
      deps.recordEinvoiceIrn();
    } else if (businessAction === "item-create") {
      deps.createInventoryItemFromForm();
    } else if (businessAction === "item-deactivate") {
      deps.deactivateInventoryItem(button.getAttribute("data-item-id") || "");
    } else if (businessAction === "stock-register-load") {
      deps.loadStockMovements();
      deps.loadStockRegister();
    } else if (businessAction === "stock-movement-create") {
      deps.createStockMovementFromForm();
    } else if (businessAction === "closing-stock-post") {
      deps.postClosingStock();
    } else if (businessAction === "itc-preview") {
      deps.previewItcReversalsFromInput();
    } else if (businessAction === "itc-reverse") {
      deps.reverseItcForBill(button.getAttribute("data-bill-id") || "");
    } else if (businessAction === "itc-reclaim") {
      deps.reclaimItcForBill(button.getAttribute("data-bill-id") || "");
    } else if (businessAction === "bill-mark-paid") {
      deps.markBillPaidFull(button.getAttribute("data-bill-id") || "", button.getAttribute("data-bill-amount") || "0");
    } else if (businessAction === "open-create-credit-note") {
      deps.openCreditNoteCreate();
    } else if (businessAction === "add-cn-line") {
      deps.addCnLine();
    } else if (businessAction === "remove-cn-line") {
      deps.removeCnLine(button.getAttribute("data-line-id") || "");
    } else if (businessAction === "save-credit-note") {
      deps.submitCreditNote();
    } else if (businessAction === "cn-back") {
      deps.setCreditNoteView("list");
    } else if (businessAction === "view-credit-note") {
      deps.openCreditNoteDetail(button.getAttribute("data-cn-id") || "");
    } else if (businessAction === "print-credit-note") {
      deps.printCreditNoteDetail();
    } else if (businessAction === "export-credit-note-json") {
      deps.downloadCreditNoteJson();
    } else if (businessAction === "begin-reverse-cn") {
      deps.creditUi.reverseOpen = true;
      deps.rerenderCreditNoteIfActive();
    } else if (businessAction === "cancel-reverse-cn") {
      deps.creditUi.reverseOpen = false;
      deps.rerenderCreditNoteIfActive();
    } else if (businessAction === "confirm-reverse-cn") {
      const noteId = button.getAttribute("data-cn-id") || "";
      const dateInput = document.querySelector("[data-reversal-date]");
      deps.cancelCreditNote(noteId, dateInput?.value || "");
    } else if (businessAction === "open-create-debit-note") {
      deps.openDebitNoteCreate();
    } else if (businessAction === "add-dn-line") {
      deps.addDnLine();
    } else if (businessAction === "remove-dn-line") {
      deps.removeDnLine(button.getAttribute("data-line-id") || "");
    } else if (businessAction === "save-debit-note") {
      deps.submitDebitNote();
    } else if (businessAction === "dn-back") {
      deps.setDebitNoteView("list");
    } else if (businessAction === "view-debit-note") {
      deps.openDebitNoteDetail(button.getAttribute("data-dn-id") || "");
    } else if (businessAction === "print-debit-note") {
      deps.printDebitNoteDetail();
    } else if (businessAction === "export-debit-note-json") {
      deps.downloadDebitNoteJson();
    } else if (businessAction === "begin-reverse-dn") {
      deps.debitUi.reverseOpen = true;
      deps.rerenderDebitNoteIfActive();
    } else if (businessAction === "cancel-reverse-dn") {
      deps.debitUi.reverseOpen = false;
      deps.rerenderDebitNoteIfActive();
    } else if (businessAction === "confirm-reverse-dn") {
      const noteId = button.getAttribute("data-dn-id") || "";
      const dateInput = document.querySelector("[data-reversal-date]");
      deps.cancelDebitNote(noteId, dateInput?.value || "");
    }

    // COA actions use their own attribute to avoid collisions with businessAction
    const coaAction = button.getAttribute("data-coa-action");
    if (coaAction === "toggle-add-form") {
      const form = document.getElementById("coa-add-form");
      if (form) form.style.display = form.style.display === "none" ? "" : "none";
    } else if (coaAction === "submit-add") {
      deps.coaHandleAddSubmit();
    } else if (coaAction === "edit-name") {
      const row = button.closest("tr[data-coa-code]");
      if (row) deps.coaEnterEditMode(row);
    } else if (coaAction === "save-name") {
      const row = button.closest("tr[data-coa-code]");
      if (row) deps.coaHandleSaveName(row);
    } else if (coaAction === "cancel-name") {
      const row = button.closest("tr[data-coa-code]");
      if (row) deps.coaExitEditMode(row);
    } else if (coaAction === "clear-filter") {
      deps.coaTypeFilter = "";
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    } else if (coaAction === "ca-invite-submit") {
      const form = button.closest("[data-ca-invite-form]");
      if (!form) return;
      const email = (form.querySelector("[name=email]")?.value || "").trim();
      const full_name = (form.querySelector("[name=full_name]")?.value || "").trim();
      if (!email || !full_name) {
        deps.caInviteError = "Please fill in both name and email.";
        deps.caInviteSuccess = "";
        deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
        return;
      }
      button.disabled = true;
      const result = await deps.apiRequest("mitrabooks", "/api/v1/business/ca/invite", {
        method: "POST",
        body: JSON.stringify({ email, full_name }),
        timeoutMs: 30000,
      });
      button.disabled = false;
      if (result.ok) {
        const payload = result.payload || {};
        if (payload.email_sent) {
          deps.caInviteSuccess = `${payload.resent ? "Invite link resent" : "Invite link sent"} to ${email}.`;
          deps.caInviteError = "";
        } else {
          deps.caInviteSuccess = "";
          deps.caInviteError = `CA account was provisioned, but the credential email was not delivered: ${payload.email_error || "SMTP delivery failed."}`;
        }
        form.reset();
        deps.loadCaAccessUsers();
      } else {
        deps.caInviteError = result.payload?.detail || `Failed to send invite (HTTP ${result.status}).`;
        deps.caInviteSuccess = "";
        deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
      }
    } else if (coaAction === "ca-resend") {
      const email = button.getAttribute("data-ca-email");
      const full_name = button.getAttribute("data-ca-name") || "";
      if (!email) return;
      if (!confirm(`Resend the secure invite link to ${email}? The recipient will set their password on first use.`)) return;
      button.disabled = true;
      const result = await deps.apiRequest("mitrabooks", "/api/v1/business/ca/invite", {
        method: "POST",
        body: JSON.stringify({ email, full_name }),
        timeoutMs: 30000,
      });
      button.disabled = false;
      if (result.ok) {
        const payload = result.payload || {};
        if (payload.email_sent) {
          deps.caInviteSuccess = `New invite link sent to ${email}.`;
          deps.caInviteError = "";
        } else {
          deps.caInviteSuccess = "";
          deps.caInviteError = `Account refreshed but email delivery failed: ${payload.email_error || "SMTP not configured."}`;
        }
        deps.loadCaAccessUsers();
      } else {
        alert(result.payload?.detail || `Resend failed (HTTP ${result.status}).`);
      }
    } else if (coaAction === "ca-delete") {
      const inviteId = button.getAttribute("data-ca-invite-id");
      const email = button.getAttribute("data-ca-email");
      if (!inviteId) return;
      if (!confirm(`Permanently delete the CA record for ${email}? This cannot be undone.`)) return;
      button.disabled = true;
      const result = await deps.apiRequest("mitrabooks", `/api/v1/business/ca/invite/${encodeURIComponent(inviteId)}/cancel`, {
        method: "POST",
      });
      button.disabled = false;
      if (result.ok) {
        deps.loadCaAccessUsers();
      } else {
        alert(result.payload?.detail || `Delete failed (HTTP ${result.status}).`);
      }
    } else if (coaAction === "ca-reinstate") {
      const userId = button.getAttribute("data-ca-user-id");
      const email = button.getAttribute("data-ca-email");
      if (!userId) return;
      if (!confirm(`Reinstate CA access for ${email}? They will be able to log in again.`)) return;
      button.disabled = true;
      const result = await deps.apiRequest("mitrabooks", `/api/v1/business/ca/${encodeURIComponent(userId)}/reinstate`, {
        method: "POST",
      });
      button.disabled = false;
      if (result.ok) {
        deps.loadCaAccessUsers();
      } else {
        alert(result.payload?.detail || `Reinstate failed (HTTP ${result.status}).`);
      }
    } else if (coaAction === "ca-revoke") {
      const userId = button.getAttribute("data-ca-user-id");
      const email = button.getAttribute("data-ca-email");
      if (!userId) return;
      if (!confirm(`Revoke CA access for ${email}? They will no longer be able to log in.`)) return;
      button.disabled = true;
      const result = await deps.apiRequest("mitrabooks", `/api/v1/business/ca/${encodeURIComponent(userId)}/revoke`, {
        method: "POST",
      });
      button.disabled = false;
      if (result.ok) {
        deps.loadCaAccessUsers();
      } else {
        alert(result.payload?.detail || `Revoke failed (HTTP ${result.status}).`);
      }
    }
  });
  deps.dashboardPreview.addEventListener("input", (event) => {
    if (event.target.closest("[data-invoice-form]")) {
      deps.updateInvoiceTotalsDisplay();
    } else if (event.target.closest("[data-bill-form]")) {
      deps.updateBillTotalsDisplay();
    } else if (event.target.closest("[data-cn-form]")) {
      deps.updateCnTotalsDisplay();
    } else if (event.target.closest("[data-dn-form]")) {
      deps.updateDnTotalsDisplay();
    }
  });
  deps.dashboardPreview.addEventListener("change", (event) => {
    if (event.target.id === "coa-type-filter") {
      deps.coaTypeFilter = event.target.value;
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
      return;
    }
    if (!["is_inter_state", "is_reverse_charge", "tds_section", "tcs_section", "supply_type"].includes(event.target.name)) {
      return;
    }
    if (event.target.closest("[data-invoice-form]")) {
      deps.updateInvoiceTotalsDisplay();
    } else if (event.target.closest("[data-bill-form]")) {
      deps.updateBillTotalsDisplay();
    } else if (event.target.closest("[data-cn-form]")) {
      deps.updateCnTotalsDisplay();
    } else if (event.target.closest("[data-dn-form]")) {
      deps.updateDnTotalsDisplay();
    }
  });
  deps.dashboardPreview.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    const input = event.target.closest("[data-mandir-list] input, [data-mandir-list] select, [data-business-list] input, [data-business-list] select");
    if (!input) {
      const accountingInput = event.target.closest("[data-accounting-drilldown] input, [data-accounting-drilldown] select");
      if (!accountingInput) {
        return;
      }
      event.preventDefault();
      deps.applyAccountingDrilldownFilters();
      return;
    }
    event.preventDefault();
    const mandirPanel = input.closest("[data-mandir-list]");
    const businessPanel = input.closest("[data-business-list]");
    if (mandirPanel) {
      deps.applyMandirListFilter(mandirPanel.getAttribute("data-mandir-list") || "");
    } else if (businessPanel) {
      deps.applyBusinessListFilter(businessPanel.getAttribute("data-business-list") || "");
    }
  });
  deps.dashboardPreview.addEventListener("input", (event) => {
    const field = event.target.closest("[data-ca-client-form] input, [data-ca-client-form] select");
    if (!field || !field.name) {
      return;
    }
    deps.caClientDraft = {
      ...deps.caClientDraft,
      [field.name]: field.value,
    };
  });
  deps.dashboardPreview.addEventListener("submit", (event) => {
    const mandirForm = event.target.closest("[data-mandir-create-form]");
    const mandirComplianceForm = event.target.closest("[data-mandir-compliance-form]");
    const caClientForm = event.target.closest("[data-ca-client-form]");
    const caDocumentForm = event.target.closest("[data-ca-document-form]");
    const caFilterForm = event.target.closest("[data-ca-filter-form]");
    if (!mandirForm && !mandirComplianceForm && !caClientForm && !caDocumentForm && !caFilterForm) {
      return;
    }
    event.preventDefault();
    if (mandirForm) {
      deps.submitMandirCreateForm(mandirForm);
    } else if (mandirComplianceForm) {
      deps.submitMandirComplianceForm(mandirComplianceForm);
    } else if (caClientForm) {
      deps.createCaClient(caClientForm);
    } else if (caDocumentForm) {
      deps.createCaPracticeDocument(caDocumentForm);
    } else if (caFilterForm) {
      const formData = new FormData(caFilterForm);
      deps.caPracticeFilters = {
        status: String(formData.get("status") || "").trim(),
        client_name: String(formData.get("client_name") || "").trim(),
        assigned_to: String(formData.get("assigned_to") || "").trim(),
        priority: String(formData.get("priority") || "").trim(),
      };
      deps.loadCaPracticeDocuments();
    }
  });
  deps.entitlementForm.addEventListener("submit", (event) => {
    event.preventDefault();
    deps.submitTenantEntitlements();
  });
  deps.mandirVerificationForm.addEventListener("submit", (event) => {
    event.preventDefault();
    deps.submitMandirPublicPaymentVerification();
  });
  deps.mandirRejectionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    deps.submitMandirPublicPaymentRejection();
  });
  deps.mandirCorrectionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    deps.submitMandirPublicPaymentCorrection();
  });
  document.getElementById("entitlement-close").addEventListener("click", () => deps.entitlementDialog.close());
  document.getElementById("entitlement-cancel").addEventListener("click", () => deps.entitlementDialog.close());
  document.getElementById("mandir-verification-close").addEventListener("click", () => deps.mandirVerificationDialog.close());
  document.getElementById("mandir-verification-cancel").addEventListener("click", () => deps.mandirVerificationDialog.close());
  document.getElementById("mandir-rejection-close").addEventListener("click", () => deps.mandirRejectionDialog.close());
  document.getElementById("mandir-rejection-cancel").addEventListener("click", () => deps.mandirRejectionDialog.close());
  document.getElementById("mandir-correction-close").addEventListener("click", () => deps.mandirCorrectionDialog.close());
  document.getElementById("mandir-correction-cancel").addEventListener("click", () => deps.mandirCorrectionDialog.close());
  document.getElementById("receipt-preview-close").addEventListener("click", deps.closeReceiptPreview);
  document.getElementById("mandir-cancel-receipt-close").addEventListener("click", () => deps.mandirCancelReceiptDialog.close());
  document.getElementById("mandir-cancel-receipt-cancel").addEventListener("click", () => deps.mandirCancelReceiptDialog.close());
  deps.mandirCancelReceiptForm.addEventListener("submit", (event) => {
    event.preventDefault();
    deps.submitMandirCancelReceipt();
  });
  deps.receiptPreviewDialog.addEventListener("close", () => {
    deps.receiptPreviewFrame.removeAttribute("src");
    if (deps.activeReceiptPreviewObjectUrl) {
      window.URL.revokeObjectURL(deps.activeReceiptPreviewObjectUrl);
      deps.activeReceiptPreviewObjectUrl = "";
    }
  });
  const businessPartyCreateDialog = document.getElementById("business-party-create-dialog");
  const businessPartyCreateForm = document.getElementById("business-party-create-form");
  const businessPartyEditDialog = document.getElementById("business-party-edit-dialog");
  const businessPartyEditForm = document.getElementById("business-party-edit-form");

  if (businessPartyCreateForm) {
    businessPartyCreateForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = document.getElementById("business-party-name")?.value || "";
      const party_type = document.getElementById("business-party-type")?.value || "customer";
      const gstin = document.getElementById("business-party-gstin")?.value || "";
      const pan = document.getElementById("business-party-pan")?.value || "";
      const city = document.getElementById("business-party-city")?.value || "";
      const state = document.getElementById("business-party-state")?.value || "";
      const pincode = document.getElementById("business-party-pincode")?.value || "";
      if (!name.trim()) {
        deps.setLoginStatus("warn", "Party name required", "Enter a name for the party.");
        return;
      }

      deps.createBusinessParty({ name, party_type, gstin, pan, city, state, pincode });
    });
  }

  if (businessPartyEditForm) {
    businessPartyEditForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const partyId = document.getElementById("business-party-edit-id")?.value || "";
      const name = document.getElementById("business-party-edit-name")?.value || "";
      const party_type = document.getElementById("business-party-edit-type")?.value || "customer";
      const gstin = document.getElementById("business-party-edit-gstin")?.value || "";
      const pan = document.getElementById("business-party-edit-pan")?.value || "";
      const city = document.getElementById("business-party-edit-city")?.value || "";
      const state = document.getElementById("business-party-edit-state")?.value || "";
      const pincode = document.getElementById("business-party-edit-pincode")?.value || "";
      if (!name.trim()) {
        deps.setLoginStatus("warn", "Party name required", "Enter a name for the party.");
        return;
      }

      deps.updateBusinessParty(partyId, { name, party_type, gstin, pan, city, state, pincode });
    });
  }

  document.getElementById("business-party-create-close")?.addEventListener("click", () => businessPartyCreateDialog?.close());
  document.getElementById("business-party-create-cancel")?.addEventListener("click", () => businessPartyCreateDialog?.close());
  document.getElementById("business-party-edit-close")?.addEventListener("click", () => businessPartyEditDialog?.close());
  document.getElementById("business-party-edit-cancel")?.addEventListener("click", () => businessPartyEditDialog?.close());

  const businessVoucherCreateDialog = document.getElementById("business-voucher-create-dialog");
  const businessVoucherCreateForm = document.getElementById("business-voucher-create-form");

  if (businessVoucherCreateForm) {
    businessVoucherCreateForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const voucherType = document.getElementById("business-voucher-type-select")?.value || "";
      const date = document.getElementById("business-voucher-date")?.value || "";

      if (!voucherType) {
        deps.setLoginStatus("warn", "Voucher type required", "Select a voucher type.");
        return;
      }

      if (!date) {
        deps.setLoginStatus("warn", "Date required", "Enter the voucher date.");
        return;
      }

      deps.createBusinessVoucherByType(voucherType, date);
    });

    // Add event listener for voucher type selector
    document.getElementById("business-voucher-type-select")?.addEventListener("change", (event) => {
      const voucherType = event.target.value;
      deps.updateVoucherTypeForm(voucherType);
    });
  }

  document.getElementById("business-voucher-create-close")?.addEventListener("click", () => businessVoucherCreateDialog?.close());
  document.getElementById("business-voucher-create-cancel")?.addEventListener("click", () => businessVoucherCreateDialog?.close());
  businessVoucherCreateDialog?.addEventListener("keydown", deps.handleVoucherDialogKeyboard);
  businessVoucherCreateDialog?.addEventListener("click", (event) => {
    const button = event.target.closest('[data-business-action="remove-voucher-line"]');
    if (!button) {
      return;
    }
    event.preventDefault();
    deps.removeVoucherLine(button.getAttribute("data-line-id") || "");
  });

  document.getElementById("business-voucher-add-line")?.addEventListener("click", (event) => {
    event.preventDefault();
    deps.addVoucherLine();
  });

  const auditEventDetailDialog = document.getElementById("audit-event-detail-dialog");
  document.getElementById("audit-event-detail-close")?.addEventListener("click", () => auditEventDetailDialog?.close());
  document.getElementById("audit-event-detail-cancel")?.addEventListener("click", () => auditEventDetailDialog?.close());

  deps.dashboardPreview.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    const input = event.target.closest("[data-business-list='audit'] input, [data-business-list='audit'] select");
    if (!input) {
      return;
    }
    event.preventDefault();
    deps.applyAuditFilters();
  });

  document.getElementById("mode-mitrabooks").addEventListener("click", () => deps.setExperience("mitrabooks"));
  document.getElementById("mode-platform").addEventListener("click", () => deps.setExperience("platform"));
  document.getElementById("mode-mandir").addEventListener("click", () => deps.setExperience("mandir"));
  document.getElementById("mode-gruha").addEventListener("click", () => deps.setExperience("gruha"));

}
