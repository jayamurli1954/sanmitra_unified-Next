// ====================================================================
// SECTION: SHELL UI — theme toggles, sidebar org/FY, quick actions
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: listener bodies unchanged aside from deps.<binding> for shell
// bindings (keeps mutable let assignment semantics). Wire via initShellUi.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initShellUi(injected) {
  deps = injected;
  installShellUi();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initShellUi() must be called before registering shell UI handlers");
  }
  return deps;
}

function installShellUi() {
  const deps = requireDeps();

  // Theme toggle buttons (if they exist in the sidebar)
  const themeDarkBtn = document.getElementById("theme-dark-btn");
  const themeLightBtn = document.getElementById("theme-light-btn");

  if (themeDarkBtn) {
    themeDarkBtn.addEventListener("click", () => deps.setTheme("dark"));
  }
  if (themeLightBtn) {
    themeLightBtn.addEventListener("click", () => deps.setTheme("light"));
  }

  // ============================================
  // SIDEBAR UI INTERACTIONS (Phase 1C)
  // ============================================

  /**
   * Org Selector Dropdown Toggle
   */
  const orgTrigger = document.getElementById("org-trigger");
  const orgMenu = document.getElementById("org-menu");
  const orgSelector = document.getElementById("org-selector");
  const orgOptions = document.querySelectorAll(".org-option");

  if (orgTrigger) {
    orgTrigger.addEventListener("click", () => {
      const isOpen = !orgMenu.hidden;
      orgMenu.hidden = isOpen;
      orgSelector.classList.toggle("open", !isOpen);
    });
  }

  // Close org dropdown when option is selected
  orgOptions.forEach((option) => {
    option.addEventListener("click", (e) => {
      const orgType = e.currentTarget.getAttribute("data-org");
      const selectorMeta = deps.orgSelectorMeta[orgType] || deps.orgSelectorMeta.BUSINESS;
      deps.selectedOrgType = orgType;
      deps.syncOrgSelectorOptions(orgType);
      orgMenu.hidden = true;
      orgSelector.classList.remove("open");
      if (orgType === "BUSINESS" || orgType === "PROFESSIONAL" || orgType === "CA_PRACTICE") {
        deps.setLoginStatus("ok", selectorMeta.statusTitle, selectorMeta.statusCopy);
      } else {
        deps.setLoginStatus("warn", selectorMeta.statusTitle, selectorMeta.statusCopy);
      }
      deps.updateTrustedContextUi();
      if (deps.currentExperience === "mitrabooks") {
        deps.activeBusinessWorkspace = "overview";
        deps.syncBusinessNavActiveState();
        deps.dashboardPreview.innerHTML = deps.renderDashboardPreview(deps.experienceConfig.mitrabooks);
        if (orgType === "BUSINESS" && deps.hasTrustedSession()) {
          deps.loadBusinessDashboardStats();
        } else if (orgType === "CA_PRACTICE") {
          deps.lastCaDocumentsResult = null;
          deps.lastCaDocuments = [];
          deps.loadCaPracticeDocuments();
        }
      }
    });
  });

  /**
   * FY Selector Dropdown Toggle
   */
  const fyTrigger = document.getElementById("fy-trigger");
  const fyMenu = document.getElementById("fy-menu");
  const fyOptions = document.querySelectorAll(".fy-option");

  if (fyTrigger) {
    fyTrigger.addEventListener("click", () => {
      const isOpen = !fyMenu.hidden;
      fyMenu.hidden = isOpen;
    });
  }

  // Close FY dropdown when option is selected
  fyOptions.forEach((option) => {
    option.addEventListener("click", (e) => {
      const fy = e.currentTarget.getAttribute("data-fy");
      fyOptions.forEach((o) => o.classList.remove("active"));
      e.currentTarget.classList.add("active");
      fyMenu.hidden = true;
      document.getElementById("current-fy").textContent = `FY ${fy}`;
    });
  });

  /**
   * Close dropdowns when clicking outside
   */
  document.addEventListener("click", (e) => {
    // Close org dropdown if click is outside
    if (orgMenu && orgSelector && !orgSelector.contains(e.target)) {
      orgMenu.hidden = true;
      orgSelector.classList.remove("open");
    }
    // Close FY dropdown if click is outside
    if (fyMenu && fyTrigger && !fyTrigger.closest(".fy-selector").contains(e.target)) {
      fyMenu.hidden = true;
    }
  });

  // ============================================

  /**
   * Quick Action Buttons
   */
  const btnQuickParty = document.getElementById("btn-quick-party");
  const btnQuickJournal = document.getElementById("btn-quick-post-journal");

  async function openVoucherWorkspaceAndDialog() {
    deps.activeBusinessWorkspace = "vouchers";
    deps.syncBusinessNavActiveState();
    deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    await deps.openBusinessCreateVoucherDialog();
  }

  function openBusinessDocumentWorkspaceAndForm(workspace) {
    deps.activeBusinessWorkspace = workspace;
    deps.syncBusinessNavActiveState();
    deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
    if (workspace === "sales") {
      deps.openInvoiceCreate();
    } else if (workspace === "bills") {
      deps.openBillCreate();
    } else if (workspace === "credit-notes") {
      deps.openCreditNoteCreate();
    } else if (workspace === "debit-notes") {
      deps.openDebitNoteCreate();
    }
  }

  function activeBusinessDocumentFormConfig() {
    if (deps.activeBusinessWorkspace === "sales" && deps.salesUi.view === "create" && document.querySelector("[data-invoice-form]")) {
      return { addLine: deps.addInvoiceLine, submit: deps.submitInvoice };
    }
    if (deps.activeBusinessWorkspace === "bills" && deps.purchaseUi.view === "create" && document.querySelector("[data-bill-form]")) {
      return { addLine: deps.addBillLine, submit: deps.submitBill };
    }
    if (deps.activeBusinessWorkspace === "credit-notes" && deps.creditUi.view === "create" && document.querySelector("[data-cn-form]")) {
      return { addLine: deps.addCnLine, submit: deps.submitCreditNote };
    }
    if (deps.activeBusinessWorkspace === "debit-notes" && deps.debitUi.view === "create" && document.querySelector("[data-dn-form]")) {
      return { addLine: deps.addDnLine, submit: deps.submitDebitNote };
    }
    return null;
  }

  function handleBusinessDocumentEntryKeyboard(event) {
    if (deps.currentExperience !== "mitrabooks" || !deps.hasTrustedSession()) {
      return;
    }
    if (document.querySelector("dialog[open]")) {
      return;
    }
    const key = String(event.key || "").toLowerCase();
    if (event.ctrlKey && event.altKey) {
      const workspaceByKey = { i: "sales", b: "bills", c: "credit-notes", d: "debit-notes" };
      const workspace = workspaceByKey[key];
      if (workspace) {
        event.preventDefault();
        openBusinessDocumentWorkspaceAndForm(workspace);
      }
      return;
    }

    const formConfig = activeBusinessDocumentFormConfig();
    if (!formConfig) {
      return;
    }
    if (event.ctrlKey && event.key === "Enter") {
      event.preventDefault();
      formConfig.submit();
      return;
    }
    if (event.altKey && !event.ctrlKey && key === "l") {
      event.preventDefault();
      formConfig.addLine();
    }
  }

  if (btnQuickParty) {
    btnQuickParty.addEventListener("click", () => {
      deps.activeBusinessWorkspace = "parties";
      deps.syncBusinessNavActiveState();
      deps.dashboardPreview.innerHTML = deps.renderBusinessWorkspace();
      deps.openBusinessCreatePartyDialog();
    });
  }

  if (btnQuickJournal) {
    btnQuickJournal.addEventListener("click", async () => {
      await openVoucherWorkspaceAndDialog();
    });
  }

  document.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey && event.altKey && event.key.toLowerCase() === "v")) {
      return;
    }
    if (document.querySelector("dialog[open]")) {
      return;
    }
    if (deps.currentExperience !== "mitrabooks" || !deps.hasTrustedSession()) {
      return;
    }
    event.preventDefault();
    openVoucherWorkspaceAndDialog();
  });

  document.addEventListener("keydown", handleBusinessDocumentEntryKeyboard);

  /**
   * Update page title and breadcrumb based on current view
   * @param {string} parentName - Parent breadcrumb name
   * @param {string} currentName - Current breadcrumb name
   * @param {string} pageTitle - Full page title
   */

}
