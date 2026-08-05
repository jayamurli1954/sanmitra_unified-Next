// ====================================================================
// SECTION: BUSINESS WORKSPACE DISPATCHER + ROUTER
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessWorkspace(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let dashboardPreview;
let nav;
let topbarCurrent;

export function initBusinessWorkspace(injected) {
  deps = injected;
  dashboardPreview = injected.dashboardPreview;
  nav = injected.nav;
  topbarCurrent = injected.topbarCurrent;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessWorkspace() must be called before using business workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function setActiveBusinessWorkspace(value) { requireDeps().setActiveBusinessWorkspace(value); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getSelectedOrgType() { return requireDeps().getSelectedOrgType(); }
function setSelectedOrgType(value) { requireDeps().setSelectedOrgType(value); }
function getOrgSelectorMeta() { return requireDeps().getOrgSelectorMeta(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessVouchers() { return requireDeps().getLastBusinessVouchers(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastVoucherApprovalQueue() { return requireDeps().getLastVoucherApprovalQueue(); }
function getLastAuditEvents() { return requireDeps().getLastAuditEvents(); }
function getSalesUi() { return requireDeps().getSalesUi(); }
function getPurchaseUi() { return requireDeps().getPurchaseUi(); }
function getCreditUi() { return requireDeps().getCreditUi(); }
function getDebitUi() { return requireDeps().getDebitUi(); }
function getHrUi() { return requireDeps().getHrUi(); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function setActiveSettingsDetailId(...args) { return requireDeps().setActiveSettingsDetailId(...args); }
function hasTrustedSession(...args) { return requireDeps().hasTrustedSession(...args); }
function updatePageHeader(...args) { return requireDeps().updatePageHeader(...args); }
function renderMitraBooksSettingsWorkspace(...args) { return requireDeps().renderMitraBooksSettingsWorkspace(...args); }
function renderCaPracticePortalWorkspace(...args) { return requireDeps().renderCaPracticePortalWorkspace(...args); }
function renderBusinessPartiesListFilters(...args) { return requireDeps().renderBusinessPartiesListFilters(...args); }
function renderBusinessPartiesTable(...args) { return requireDeps().renderBusinessPartiesTable(...args); }
function renderVoucherApprovalQueuePanel(...args) { return requireDeps().renderVoucherApprovalQueuePanel(...args); }
function renderBusinessVouchersListFilters(...args) { return requireDeps().renderBusinessVouchersListFilters(...args); }
function renderBusinessVouchersTable(...args) { return requireDeps().renderBusinessVouchersTable(...args); }
function renderAuditListFilters(...args) { return requireDeps().renderAuditListFilters(...args); }
function renderAuditEventsTable(...args) { return requireDeps().renderAuditEventsTable(...args); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function renderBusinessReportsWorkspace(...args) { return requireDeps().renderBusinessReportsWorkspace(...args); }
function renderBusinessSalesWorkspace(...args) { return requireDeps().renderBusinessSalesWorkspace(...args); }
function renderBusinessPurchaseWorkspace(...args) { return requireDeps().renderBusinessPurchaseWorkspace(...args); }
function renderBusinessCreditNoteWorkspace(...args) { return requireDeps().renderBusinessCreditNoteWorkspace(...args); }
function renderBusinessDebitNoteWorkspace(...args) { return requireDeps().renderBusinessDebitNoteWorkspace(...args); }
function renderBusinessCoaWorkspace(...args) { return requireDeps().renderBusinessCoaWorkspace(...args); }
function renderFinancialHealthWorkspace(...args) { return requireDeps().renderFinancialHealthWorkspace(...args); }
function renderHrWorkspace(...args) { return requireDeps().renderHrWorkspace(...args); }
function renderOfficeAiWorkspace(...args) { return requireDeps().renderOfficeAiWorkspace(...args); }
function renderManufacturingWorkspace(...args) { return requireDeps().renderManufacturingWorkspace(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function loadBusinessDashboardStats(...args) { return requireDeps().loadBusinessDashboardStats(...args); }
function loadBusinessParties(...args) { return requireDeps().loadBusinessParties(...args); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessVouchers(...args) { return requireDeps().loadBusinessVouchers(...args); }
function loadVoucherApprovalQueue(...args) { return requireDeps().loadVoucherApprovalQueue(...args); }
function loadAuditEvents(...args) { return requireDeps().loadAuditEvents(...args); }
function refreshCurrentAccountingDrilldown(...args) { return requireDeps().refreshCurrentAccountingDrilldown(...args); }
function refreshCurrentBusinessReport(...args) { return requireDeps().refreshCurrentBusinessReport(...args); }
function loadInvoiceSettings(...args) { return requireDeps().loadInvoiceSettings(...args); }
function loadBusinessInvoices(...args) { return requireDeps().loadBusinessInvoices(...args); }
function loadBusinessAdminSettings(...args) { return requireDeps().loadBusinessAdminSettings(...args); }
function loadBusinessPartiesForHealth(...args) { return requireDeps().loadBusinessPartiesForHealth(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function loadBusinessDataHealth(...args) { return requireDeps().loadBusinessDataHealth(...args); }
function loadBusinessBills(...args) { return requireDeps().loadBusinessBills(...args); }
function loadCreditNotes(...args) { return requireDeps().loadCreditNotes(...args); }
function loadDebitNotes(...args) { return requireDeps().loadDebitNotes(...args); }
function setCoaTypeFilter(...args) { return requireDeps().setCoaTypeFilter(...args); }
function resetCaPracticeWorkspaceState(...args) { return requireDeps().resetCaPracticeWorkspaceState(...args); }
function isBusinessAdmin(...args) { return requireDeps().isBusinessAdmin(...args); }
function loadCaAccessUsers(...args) { return requireDeps().loadCaAccessUsers(...args); }
function loadCaClients(...args) { return requireDeps().loadCaClients(...args); }
function loadCaPracticeDocuments(...args) { return requireDeps().loadCaPracticeDocuments(...args); }
function loadHrWorkspace(...args) { return requireDeps().loadHrWorkspace(...args); }
function loadOfficeAiWorkspace(...args) { return requireDeps().loadOfficeAiWorkspace(...args); }
function setMfgTab(...args) { return requireDeps().setMfgTab(...args); }
function setMfgError(...args) { return requireDeps().setMfgError(...args); }
function loadMfgWorkspace(...args) { return requireDeps().loadMfgWorkspace(...args); }

export function renderBusinessWorkspace() {
  if (getActiveBusinessWorkspace() === "settings") {
    return renderMitraBooksSettingsWorkspace();
  }
  if (getActiveBusinessWorkspace() === "ca-access") {
    return renderCaPracticePortalWorkspace();
  }
  if (getActiveBusinessWorkspace() === "parties") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Parties</h4>
            <p>Customers and vendors for this business workspace.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-party">+ New Party</button>
        </div>
        ${renderBusinessPartiesListFilters(getLastBusinessParties().length)}
        ${renderBusinessPartiesTable(getLastBusinessParties())}
      </div>
    `;
  }
  if (getActiveBusinessWorkspace() === "vouchers") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Vouchers</h4>
            <p>Posted journal entries, payments, receipts, and contra vouchers.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-voucher" aria-keyshortcuts="Control+Alt+V">+ New Voucher</button>
        </div>
        ${renderVoucherApprovalQueuePanel(getLastVoucherApprovalQueue())}
        ${renderBusinessVouchersListFilters(getLastBusinessVouchers().length)}
        ${renderBusinessVouchersTable(getLastBusinessVouchers())}
      </div>
    `;
  }
  if (getActiveBusinessWorkspace() === "audit") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Audit Trail</h4>
            <p>All party, voucher, and account changes for compliance and troubleshooting.</p>
          </div>
        </div>
        ${renderAuditListFilters(getLastAuditEvents().length)}
        ${renderAuditEventsTable(getLastAuditEvents())}
      </div>
    `;
  }
  if (getActiveBusinessWorkspace() === "accounting") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Accounting</h4>
            <p>Chart readiness, voucher drill-down, and posted ledger checks for the active tenant.</p>
          </div>
        </div>
        ${renderAccountingDrilldownPanel()}
      </div>
    `;
  }
  // "gst-returns", "reconciliation" and "tds-tcs" are sidebar shortcuts into the
  // reports workspace (which hosts those tabs); the tab is pre-selected in setBusinessWorkspace.
  if (getActiveBusinessWorkspace() === "reports"
      || getActiveBusinessWorkspace() === "gst-returns"
      || getActiveBusinessWorkspace() === "reconciliation"
      || getActiveBusinessWorkspace() === "tds-tcs"
      || getActiveBusinessWorkspace() === "bank-recon") {
    return renderBusinessReportsWorkspace();
  }
  if (getActiveBusinessWorkspace() === "sales") {
    return renderBusinessSalesWorkspace();
  }
  if (getActiveBusinessWorkspace() === "bills") {
    return renderBusinessPurchaseWorkspace();
  }
  if (getActiveBusinessWorkspace() === "credit-notes") {
    return renderBusinessCreditNoteWorkspace();
  }
  if (getActiveBusinessWorkspace() === "debit-notes") {
    return renderBusinessDebitNoteWorkspace();
  }
  if (getActiveBusinessWorkspace() === "coa") {
    return renderBusinessCoaWorkspace();
  }
  if (getActiveBusinessWorkspace() === "financial-health") {
    return renderFinancialHealthWorkspace();
  }
  if (getActiveBusinessWorkspace() === "hr") {
    return renderHrWorkspace();
  }
  if (getActiveBusinessWorkspace() === "office-ai") {
    return renderOfficeAiWorkspace();
  }
  if (getActiveBusinessWorkspace() === "manufacturing") {
    return renderManufacturingWorkspace();
  }
  return `
    <div class="erp-workbench-grid">
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Core Master</span>
        <h4>Parties</h4>
        <strong>${escapeHtml(getLastBusinessParties().length)}</strong>
        <p>Customers and vendors available for business posting.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="parties">Open Parties</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Posting</span>
        <h4>Vouchers</h4>
        <strong>${escapeHtml(getLastBusinessVouchers().length)}</strong>
        <p>Posted journal entries, receipts, payments, and reversals.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">Open Vouchers</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Chart</span>
        <h4>Accounts</h4>
        <strong>${escapeHtml(getLastBusinessAccounts().length)}</strong>
        <p>Tenant-owned chart of accounts loaded from accounting APIs.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="accounting">Open Accounting</button>
      </article>
    </div>
  `;
  return `
    <div class="dashboard-main-grid erp-command-grid">
      <article>
        <h4>Quick Actions</h4>
        <div class="quick-grid">
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="parties">
            <span class="quick-icon">●</span>
            <span>Parties</span>
          </button>
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">
            <span class="quick-icon">▤</span>
            <span>Vouchers</span>
          </button>
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="audit">
            <span class="quick-icon">⏱</span>
            <span>Audit</span>
          </button>
        </div>
      </article>
    </div>
  `;
}

export function setBusinessWorkspace(workspace) {
  if (getCurrentExperience() === "mitrabooks" && activeOrgSelectorType() !== "BUSINESS") {
    setSelectedOrgType("BUSINESS");
    updateTrustedContextUi();
  }
  if (workspace !== "settings") {
    setActiveSettingsDetailId("");
  }
  setActiveBusinessWorkspace(workspace);
  syncBusinessNavActiveState();
  dashboardPreview.innerHTML = workspace === "overview"
    ? renderDashboardPreview(getExperienceConfig().mitrabooks)
    : renderBusinessWorkspace();
  if (workspace === "overview" && hasTrustedSession()) {
    loadBusinessDashboardStats();
  } else if (workspace === "parties") {
    loadBusinessParties();
  } else if (workspace === "vouchers") {
    loadBusinessAccounts();
    loadBusinessVouchers();
    loadVoucherApprovalQueue(true, { surfaceErrors: false });
  } else if (workspace === "audit") {
    loadAuditEvents();
  } else if (workspace === "accounting") {
    refreshCurrentAccountingDrilldown();
  } else if (workspace === "reports" || workspace === "gst-returns" || workspace === "reconciliation" || workspace === "tds-tcs" || workspace === "bank-recon") {
    // Sidebar shortcuts open the reports workspace on a specific tab.
    if (workspace === "gst-returns") getBusinessReportState().tab = "gst-returns";
    else if (workspace === "reconciliation") getBusinessReportState().tab = "payment-allocation";
    else if (workspace === "tds-tcs") getBusinessReportState().tab = "tds";
    else if (workspace === "bank-recon") getBusinessReportState().tab = "bank-recon";
    loadBusinessAccounts();
    refreshCurrentBusinessReport();
  } else if (workspace === "sales") {
    getSalesUi().view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadInvoiceSettings();
    loadBusinessInvoices();
  } else if (workspace === "settings") {
    loadBusinessAdminSettings();
    loadBusinessAccounts();
    loadBusinessPartiesForHealth();
    loadAccountingDrilldownResult();
    loadBusinessDataHealth();
  } else if (workspace === "bills") {
    getPurchaseUi().view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadBusinessBills();
  } else if (workspace === "credit-notes") {
    getCreditUi().view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadCreditNotes();
  } else if (workspace === "debit-notes") {
    getDebitUi().view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadDebitNotes();
  } else if (workspace === "coa") {
    setCoaTypeFilter("");
    loadBusinessAccounts();
  } else if (workspace === "ca-access") {
    resetCaPracticeWorkspaceState();
    const startupLoads = [];
    if (isBusinessAdmin()) {
      startupLoads.push(loadCaAccessUsers({ rerender: false }));
    }
    startupLoads.push(loadCaClients({ rerender: false }));
    startupLoads.push(loadCaPracticeDocuments({ rerender: false }));
    Promise.allSettled(startupLoads).then(() => {
      if (getActiveBusinessWorkspace() === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    });
  } else if (workspace === "hr") {
    getHrUi().tab = "employees";
    getHrUi().error = "";
    getHrUi().selectedRunId = "";
    getHrUi().runSlips = [];
    loadHrWorkspace();
  } else if (workspace === "office-ai") {
    loadOfficeAiWorkspace();
  } else if (workspace === "manufacturing") {
    setMfgTab("cost-centres");
    setMfgError("");
    loadMfgWorkspace();
  }
}

export function syncBusinessNavActiveState() {
  const selectorOrgType = activeOrgSelectorType();
  const isPlannedOrgWorkspace = getCurrentExperience() === "mitrabooks"
    && getActiveBusinessWorkspace() === "overview"
    && selectorOrgType !== "BUSINESS";
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.businessWorkspace || "";
    const isActive = getCurrentExperience() === "mitrabooks"
      && !isPlannedOrgWorkspace
      && workspace
      && workspace === getActiveBusinessWorkspace();
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && getCurrentExperience() === "mitrabooks") {
    const labels = {
      overview: "Dashboard",
      parties: "Parties",
      vouchers: "Vouchers",
      audit: "Audit Trail",
      accounting: "Accounting",
      reports: "Financial Reports",
      sales: "Sales Invoices",
      bills: "Purchase Bills",
      "credit-notes": "Credit Notes",
      "debit-notes": "Debit Notes",
      "financial-health": "Financial Health",
      "office-ai": "OfficeMitra AI",
      "gst-returns": "GST Returns",
      "reconciliation": "Reconciliation",
      "tds-tcs": "TDS / TCS",
      "bank-recon": "Bank Reconciliation",
      "ca-access": "CA Practice Portal",
      coa: "Chart of Accounts",
      settings: "Settings",
    };
    const plannedMeta = getOrgSelectorMeta()[selectorOrgType];
    const label = isPlannedOrgWorkspace
      ? plannedMeta?.label || "Planned Workspace"
      : labels[getActiveBusinessWorkspace()] || "Dashboard";
    topbarCurrent.textContent = label;
    updatePageHeader("MitraBooks", label, `${label} Workspace`);
  }
}

