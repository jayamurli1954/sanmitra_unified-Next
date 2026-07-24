// ====================================================================
// SECTION: ORG / PLANNED-SUITE WORKSPACE RENDERERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initOrgWorkspace(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initOrgWorkspace(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initOrgWorkspace() must be called before using org workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function renderCaPracticePortalWorkspace(...args) { return requireDeps().renderCaPracticePortalWorkspace(...args); }
function renderProfessionalSuiteWorkspace(...args) { return requireDeps().renderProfessionalSuiteWorkspace(...args); }
function renderCaDocumentIntake(...args) { return requireDeps().renderCaDocumentIntake(...args); }

export function plannedOrgWorkspaceModel(orgType) {
  if (orgType === "CA_PRACTICE") {
    return {
      label: "CA Practice Portal",
      eyebrow: "Client document workflow",
      lead: "Practice-level workspace for client document intake, review status tracking, staff assignment, client-access flags, and compliance metadata.",
      kpis: [
        ["Client Tracking", "Active", "Tenant-scoped client document metadata"],
        ["Review Queue", "Active", "Document review status workflow"],
        ["Compliance", "Active", "GST, TDS, audit, ROC, and bookkeeping metadata"],
      ],
      modules: [
        ["Client document tracking", "Track each client book through tenant-scoped metadata before any future client tenant switching.", "Active"],
        ["GST and TDS metadata", "Tag documents by compliance area, due date, priority, and reviewer.", "Active"],
        ["Review queue", "Move uploaded metadata through under review, query raised, reviewed, and posted states.", "Active"],
        ["Workload summary", "Summarize client counts, staff assignment, priority work, and compliance areas from the current queue.", "Active"],
      ],
      documentIntake: {
        title: "Client document intake",
        copy: "Placeholder for uploading client bank statements, purchase bills, sales invoices, GST returns, TDS files, and supporting documents before review and posting.",
        uploadFields: [
          ["Client", "Select client book"],
          ["Document type", "Bank statement, invoice, GST, TDS"],
          ["Period", "FY 2026-27 / month"],
          ["Assigned to", "Reviewer or partner"],
        ],
        workflow: ["Uploaded", "Under review", "Query raised", "Reviewed", "Posted"],
        metrics: [
          ["Uploaded", "18", "Awaiting classification"],
          ["Under review", "7", "Staff review in progress"],
          ["Reviewed", "5", "Ready for posting"],
          ["Posted", "9", "Linked to vouchers"],
          ["Query raised", "4", "Needs client clarification"],
        ],
        rows: [
          ["Jayam Publications", "Bank statement", "May 2026", "Under review", "Reconciliation check", "-"],
          ["Kartik Enterprises", "Purchase bills", "May 2026", "Posted", "Voucher batch ready", "JV-2026-00012"],
          ["Power & Light Corp", "GST working", "Q1 2026", "Query raised", "Missing invoice support", "-"],
          ["Stellar Logistics", "Sales invoices", "May 2026", "Reviewed", "Ready for posting", "-"],
        ],
      },
      note: "Current state: tenant-scoped document metadata and review workflow are active. Deferred scope: file storage, OCR, client tenant switching, voucher posting, and filing links.",
    };
  }

  return {
    label: "Professional Suite",
    eyebrow: "Billing and invoicing",
    lead: "Service-business workspace for billing, receipts, professional client accounts, and revenue tracking using the active MitraBooks tenant context.",
    kpis: [
      ["Billing", "Active", "Service invoices through Sales"],
      ["Receivables", "Active", "Client accounts through Parties and ledger reports"],
      ["Reports", "Active", "Financial statements and health summaries"],
    ],
    modules: [
      ["Client billing", "Create service invoices with GST through the active Sales workspace.", "Active"],
      ["Client accounts", "Maintain professional clients in Parties and review balances from ledger-backed reports.", "Active"],
      ["Receipts", "Record client receipts with journal posting from the existing voucher workflow.", "Active"],
      ["Professional reports", "Use financial statements, receivables, and health summaries for practice reporting.", "Active"],
    ],
    note: "Current state: Professional Suite reuses active MitraBooks billing, parties, vouchers, and reports. Deferred scope: separate professional-only tenant context and retainer-specific automation.",
  };
}

export function renderSelectedOrgWorkspace() {
  const orgType = activeOrgSelectorType();
  if (orgType === "CA_PRACTICE") {
    return renderCaPracticePortalWorkspace();
  }
  if (orgType === "PROFESSIONAL") {
    return renderProfessionalSuiteWorkspace();
  }
  const model = plannedOrgWorkspaceModel(orgType);
  return `
    <div class="planned-org-workspace erp-workspace-panel">
      <div class="planned-org-hero">
        <div>
          <span class="workbench-kicker">${escapeHtml(model.eyebrow)}</span>
          <h3>${escapeHtml(model.label)} Workspace</h3>
          <p>${escapeHtml(model.lead)}</p>
        </div>
        <span class="pill warn">Planned</span>
      </div>

      <div class="planned-org-kpis">
        ${model.kpis.map(([title, value, copy]) => `
          <article>
            <span>${escapeHtml(title)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(copy)}</small>
          </article>
        `).join("")}
      </div>

      <div class="planned-org-module-grid">
        ${model.modules.map(([title, copy, status]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <span class="pill">${escapeHtml(status)}</span>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>
        `).join("")}
      </div>

      ${model.documentIntake ? `
        ${renderCaDocumentIntake(model.documentIntake)}
      ` : ""}

      <div class="planned-org-note">
        <strong>Implementation status</strong>
        <span>${escapeHtml(model.note)}</span>
      </div>
    </div>
  `;
}

