
// ══════════════════════════════════════════════════════════════════════
// SECTION: MODULE BOOTSTRAP — MitraBooks ERP app.js
// NOTE  : 15K-line vanilla ES-module. Split trigger: >18K lines or second developer joins.
// Use Ctrl+F '// SECTION:' to jump between sections.
// ══════════════════════════════════════════════════════════════════════

import {
  clearAccessToken,
  clearAllTokens,
  apiRequest,
  downloadApiFile,
  fetchApiFileObjectUrl,
  getAccessToken,
  getRefreshToken,
  getConfiguredApiBaseUrl,
  loadHealth,
  loadModules,
  moduleItemsFromPayload,
  renderModuleState,
  renderJson,
  setAccessToken,
  setRefreshToken,
  setConfiguredApiBaseUrl,
  statusLabel,
} from "../shared/api-client.js";
import {
  setTheme,
  initializeTheme,
} from "./modules/theme.js";
import {
  businessNavigationGroups,
  businessNavigationItems,
} from "./modules/navigation.js";
import {
  initWidgets,
  createWidgetWrapper,
  toggleWidgetCollapse,
  openWidgetSettings,
} from "./modules/widgets.js";
import {
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
import {
  initMandirFinancialReports,
  mandirReportState,
  renderMandirExpensesTable,
  renderMandirTrialBalance,
  renderMandirFinancialReports,
} from "./modules/workspaces/mandir-financial-reports.js";
import {
  initMandirTables,
  MANDIR_LIST_PAGE_SIZE,
  mandirListState,
  renderMandirPublicPaymentsTable,
  renderMandirExceptionsTable,
  mandirReceiptRowsFromLists,
  renderMandirReceiptHistoryTable,
  renderMandirDonationsTable,
  renderMandirSevaBookingsTable,
  renderMandirWorkspaceTabs,
  renderMandirListFilters,
  renderMandirPublicPaymentFilters,
  renderMandirExceptionFilters,
} from "./modules/workspaces/mandir-tables.js";
import {
  initGstReturns,
  gstReturnState,
  loadGstSettlementPreview,
  previewGstSettlementFromInput,
  postGstSettlement,
  renderGstSettlementPanel,
  loadGstr3b,
  previewGstr3bFromInput,
  downloadGstr3bJson,
  renderGstReturns,
  reconcileGstr2b,
  loadGstr4,
  previewGstr4FromInput,
  downloadGstr4Json,
  loadCmp08,
  previewCmp08FromInput,
  downloadCmp08Json,
  postCmp08Liability,
  loadGstr1,
  previewGstr1FromInput,
  downloadGstr1Json,
} from "./modules/workspaces/gst-returns.js";
import {
  initSalesInvoices,
  salesUi,
  loadInvoiceSettings,
  loadBusinessInvoices,
  syncSalesFormFromDom,
  updateInvoiceTotalsDisplay,
  computeInvoiceLine,
  invoiceStatusPill,
  customerPartyOptions,
  incomeAccountOptions,
  setBusinessSalesView,
  openInvoiceCreate,
  addInvoiceLine,
  removeInvoiceLine,
  submitInvoice,
  downloadInvoicePdf,
  openInvoiceDetail,
  cancelInvoice,
  openInvoiceSettings,
  saveInvoiceSettings,
  renderBusinessSalesWorkspace,
  rerenderSalesIfActive,
} from "./modules/documents/sales-invoices.js";

import {
  initPurchaseBills,
  purchaseUi,
  loadBusinessBills,
  syncBillFormFromDom,
  updateBillTotalsDisplay,
  setBusinessPurchaseView,
  openBillCreate,
  addBillLine,
  removeBillLine,
  submitBill,
  openBillDetail,
  loadBillAttachments,
  cancelBill,
  renderBusinessPurchaseWorkspace,
  rerenderPurchaseIfActive,
} from "./modules/documents/purchase-bills.js";

import {
  initCreditNotes,
  creditUi,
  loadCreditNotes,
  syncCnFormFromDom,
  updateCnTotalsDisplay,
  setCreditNoteView,
  openCreditNoteCreate,
  addCnLine,
  removeCnLine,
  submitCreditNote,
  openCreditNoteDetail,
  cancelCreditNote,
  renderBusinessCreditNoteWorkspace,
  rerenderCreditNoteIfActive,
} from "./modules/documents/credit-notes.js";

import {
  initDebitNotes,
  debitUi,
  loadDebitNotes,
  syncDnFormFromDom,
  updateDnTotalsDisplay,
  setDebitNoteView,
  openDebitNoteCreate,
  addDnLine,
  removeDnLine,
  submitDebitNote,
  openDebitNoteDetail,
  cancelDebitNote,
  renderBusinessDebitNoteWorkspace,
  rerenderDebitNoteIfActive,
} from "./modules/documents/debit-notes.js";

import { initEventHandlers } from "./modules/events.js";
import { initShellUi } from "./modules/shell-ui.js";

import {
  initDimensions,
  lastDimensions,
  loadDimensions,
  dimensionOptions,
  voucherDimensionPayload,
  createDimensionFromForm,
  deactivateDimension,
  loadDimensionReport,
  loadBranchConsolidatedReport,
  downloadDimensionReport,
  renderDimensionsPanel,
} from "./modules/workspaces/dimensions.js";

import {
  initFixedAssets,
  setFaFormOpen,
  faFormOpen,
  lastFixedAssets,
  loadFixedAssets,
  createFixedAssetFromForm,
  previewDepreciation,
  postDepreciationRun,
  disposeFixedAsset,
  renderFixedAssetsPanel,
} from "./modules/workspaces/fixed-assets.js";

import {
  initInventory,
  lastInventoryItems,
  loadInventoryItems,
  inventoryItemOptions,
  createInventoryItemFromForm,
  deactivateInventoryItem,
  loadInventoryPolicy,
  loadStockMovements,
  createStockMovementFromForm,
  loadStockRegister,
  loadClosingStockEntries,
  postClosingStock,
  renderInventoryPanel,
} from "./modules/workspaces/inventory.js";

import {
  initBankRecon,
  setBankCashBookType,
  bankCashBookType,
  bankAccountOptions,
  loadBankCashBook,
  loadBankReconciliation,
  uploadBankStatementFile,
  confirmBankReconMatch,
  reverseBankReconMatch,
  postBankReconStatementVoucher,
  renderBankCashBookPanel,
  renderBankReconPanel,
} from "./modules/workspaces/bank-recon.js";

import {
  initStatements,
  statementPartyId,
  statementKind,
  statementFromDate,
  statementToDate,
  loadPartyStatement,
  recordDunningSent,
  copyDunningLetter,
  renderStatementsPanel,
} from "./modules/workspaces/statements.js";

import {
  initEinvoice,
  clearEinvoiceView,
  loadEinvoiceView,
  downloadInv01Json,
  recordEinvoiceIrn,
  renderEinvoiceSection,
} from "./modules/workspaces/einvoice.js";

import {
  initTds,
  tdsQuarter,
  loadTdsRegister,
  previewTdsRegisterFromInput,
  renderTdsRegisterPanel,
} from "./modules/workspaces/tds.js";

import {
  initItcReversals,
  itcReversalAsOf,
  loadItcReversalPreview,
  previewItcReversalsFromInput,
  reverseItcForBill,
  reclaimItcForBill,
  markBillPaidFull,
  renderItcReversalPanel,
} from "./modules/workspaces/itc-reversals.js";

import {
  initPeriodLocks,
  loadPeriodLocks,
  setGstPeriodLock,
  lockGstPeriodFromInput,
  renderPeriodLocksPanel,
} from "./modules/workspaces/period-locks.js";

import {
  initOpeningYearEnd,
  downloadObTemplate,
  previewOpeningBalances,
  postOpeningBalances,
  downloadObExport,
  downloadViTemplate,
  previewBulkVouchers,
  postBulkVouchers,
  previewYearEnd,
  postYearEndClose,
  renderOpeningYearEndPanel,
} from "./modules/workspaces/opening-yearend.js";

import {
  initPaymentAllocation,
  loadBusinessAging,
  setAgingKind,
  loadUnallocatedPayments,
  setAllocationKind,
  selectAllocationPayment,
  setAllocationLineAmount,
  applyFifoSuggestion,
  submitAllocation,
  loadAllocationReconciliation,
  renderBusinessAging,
  renderPaymentAllocation,
} from "./modules/workspaces/payment-allocation.js";

import {
  initAuditTrail,
  lastAuditEvents,
  loadAuditEvents,
  renderAuditEventsTable,
  renderAuditListFilters,
  openAuditEventDetailDialog,
  applyAuditFilters,
  resetAuditFilters,
  pageAuditList,
} from "./modules/workspaces/audit-trail.js";

import {
  initGruhamitra,
  activeGruhaWorkspace,
  lastGruhaData,
  renderGruhaDashboard,
  loadGruhaDashboard,
  setGruhaWorkspace,
} from "./modules/workspaces/gruhamitra.js";

import {
  initFinancialReports,
  lastBusinessTrialBalance,
  lastBusinessProfitLoss,
  lastBusinessBalanceSheet,
  lastBusinessReceivables,
  lastBusinessPayables,
  lastBusinessGeneralLedger,
  loadBusinessTrialBalance,
  loadBusinessProfitLoss,
  loadBusinessBalanceSheet,
  loadBusinessReceivablesPayables,
  loadBusinessGeneralLedger,
  loadBusinessAllLedgers,
  reportDateControls,
  renderBusinessTrialBalance,
  renderBusinessProfitLoss,
  renderBusinessBalanceSheet,
  renderBusinessGeneralLedger,
  renderBusinessReceivablesPayables,
  setBusinessReportTab,
  applyBusinessReportFilter,
  loadBusinessReportLedgerFromSelect,
} from "./modules/workspaces/financial-reports.js";

const APP_KEY = "mitrabooks";
const DEFAULT_DEPLOYED_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com";
const DEFAULT_MITRABOOKS_LOGIN_EMAIL = "business.admin@sanmitra.local";
const LOGIN_EMAIL_STORAGE_KEY = "sanmitra_mitrabooks_login_email";
const LOGIN_REQUEST_TIMEOUT_MS = 20000;
const initialAuthParams = new URLSearchParams(window.location.search || "");
let pendingPasswordResetToken = initialAuthParams.get("action") === "reset"
  ? String(initialAuthParams.get("token") || "").trim()
  : "";
const EXPERIENCE_APP_KEYS = {
  mitrabooks: "mitrabooks",
  platform: "mitrabooks",
  mandir: "mandirmitra",
  gruha: "gruhamitra",
};


// ══════════════════════════════════════════════════════════════════════
// SECTION: EXPERIENCE DETECTION + PRODUCT SHELL
// NOTE  : isMandirHost, isGruhaHost, isProductionShell, initialExperience, experienceConfig
// ══════════════════════════════════════════════════════════════════════

function isMandirHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "mandirmitra.sanmitratech.in"
    || host === "www.mandirmitra.sanmitratech.in"
    || host.includes("mandirmitra");
}

function isGruhaHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "gruhamitra.sanmitratech.in"
    || host === "www.gruhamitra.sanmitratech.in"
    || host.includes("gruhamitra");
}

function isProductionShell() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host && host !== "localhost" && host !== "127.0.0.1" && host !== "::1";
}

function initialExperience() {
  if (isMandirHost()) {
    return "mandir";
  }
  if (isGruhaHost()) {
    return "gruha";
  }
  return "mitrabooks";
}
const entitlementModulesByOrgType = {
  TEMPLE: ["temple", "accounting", "audit"],
  HOUSING: ["housing", "accounting", "audit"],
  BUSINESS: ["business", "accounting", "gst", "inventory", "audit"],
  PROFESSIONAL: ["professional", "accounting", "billing", "audit"],
};

const orgSelectorMeta = {
  BUSINESS: {
    label: "Business Suite",
    subtitle: "SME and accounting",
    statusTitle: "Business workspace active",
    statusCopy: "Using the signed-in business tenant context.",
  },
  PROFESSIONAL: {
    label: "Professional Suite",
    subtitle: "Billing and invoicing",
    statusTitle: "Professional workspace active",
    statusCopy: "Using the signed-in MitraBooks tenant context for billing, client accounts, receipts, and reports.",
  },
  CA_PRACTICE: {
    label: "CA Practice Portal",
    subtitle: "Client document workflow",
    statusTitle: "CA Practice Portal active",
    statusCopy: "Using tenant-scoped document metadata, review queue, staff assignment, and compliance tracking.",
  },
};

const experienceConfig = {
  mitrabooks: {
    title: "MitraBooks Pro",
    subtitle: "Unified Enterprise ERP",
    logo: "../assets/brand/mitrabooks-pro-logo.png",
    video: "../assets/brand/mitrabooks-pro-logo.mp4",
    theme: "",
    scopeTitle: "MitraBooks Business Workspace",
    scopeCopy: "Business, GST, inventory, parties, vouchers, and financial reports stay close to the old MitraBooks accounting layout.",
    legacyTitle: "MitraBooks workspace",
    legacyCopy: "Business, GST, inventory, parties, vouchers, and financial reports.",
    dashboard: {
      type: "business",
      stats: [
        ["Cash and Bank", "Rs. 8.4L", "available balance"],
        ["Receivables", "Rs. 2.1L", "open invoices"],
        ["Payables", "Rs. 96K", "vendor dues"],
        ["GST Filing", "Ready", "current period"],
      ],
      actions: ["Sales Voucher", "Purchase Entry", "Journal Entry", "Ledger Report", "Trial Balance", "GST Summary"],
      activity: ["Receipt posted from customer account", "Inventory purchase voucher drafted", "Month-end ledger review pending"],
    },
    modules: [
      { module_key: "business", display_name: "Dashboard", frontend_path: "/business", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounts", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "gst", display_name: "GST Compliance", frontend_path: "/gst", nav_group: "Compliance", enabled: true },
      { module_key: "inventory", display_name: "Inventory", frontend_path: "/inventory", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
    ],
  },
  platform: {
    title: "Platform Owner",
    subtitle: "Cross-module onboarding, tenant, subscription, and module status",
    logo: "../assets/brand/mitrabooks-logo.jpg",
    video: "",
    theme: "",
    scopeTitle: "Platform Owner Workspace",
    scopeCopy: "Read-only control view for MandirMitra, GruhaMitra, and MitraBooks onboarding, subscriptions, tenant status, and enabled modules.",
    legacyTitle: "Platform owner dashboard",
    legacyCopy: "Central review layer over module-wise onboarding. Approval actions are intentionally separate from this read-only view.",
    dashboard: {
      type: "platform",
      summary: [
        ["Pending Approvals", "0", "module-wise onboarding"],
        ["Active Tenants", "0", "all tracked apps"],
        ["Inactive Tenants", "0", "needs review"],
        ["Subscription Plans", "0", "configured plans"],
      ],
      appStatus: [
        ["MandirMitra", "0 pending", "0 tenants"],
        ["GruhaMitra", "0 pending", "0 tenants"],
        ["MitraBooks", "0 pending", "0 tenants"],
      ],
    },
    modules: [
      { module_key: "platform_owner", display_name: "Dashboard", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Onboarding Requests", frontend_path: "/platform-owner/onboarding", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Tenant Status", frontend_path: "/platform-owner/tenants", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Subscriptions", frontend_path: "/platform-owner/subscriptions", nav_group: "Administration", enabled: true },
    ],
  },
  mandir: {
    title: "MandirMitra",
    subtitle: "Temple, trust, donation, seva, and accounting workflows",
    logo: "../assets/brand/mandirmitra-logo.jpeg",
    video: "../assets/brand/mandirmitra-logo.mp4",
    theme: "mandir-theme",
    scopeTitle: "MandirMitra Temple Workspace",
    scopeCopy: "Preserves the old temple layout pattern: dashboard, donations, devotees, sevas, panchang, reports, and accounting.",
    legacyTitle: "MandirMitra layout mode",
    legacyCopy: "Saffron/green visual treatment and temple-first navigation are retained for user familiarity.",
    dashboard: {
      type: "mandir",
      donations: [
        ["Today's Donation", "Rs. 24,500", "18 donations"],
        ["Cumulative for Month", "Rs. 6.8L", "412 donations"],
        ["Cumulative for Year", "Rs. 74.2L", "8,902 donations"],
      ],
      sevas: [
        ["Today's Seva", "Rs. 18,000", "27 bookings"],
        ["Cumulative for Month", "Rs. 4.2L", "685 bookings"],
        ["Cumulative for Year", "Rs. 38.5L", "6,430 bookings"],
      ],
      verification: [
        ["Public UPI Payments", "9 pending", "donation and seva confirmations"],
        ["Receipt Posting", "6 ready", "verified collections awaiting receipt"],
        ["Review Queue", "3 flagged", "amount or UTR needs checking"],
      ],
      groups: [
        ["Public Payments", "Review UPI confirmations, verify UTR, then post donation or seva receipt"],
        ["Sevas", "Book Sevas, Seva Bookings / Reschedule, Seva Management"],
        ["Accounting", "Chart of Accounts, Quick Expense, Journal Entries, Reports"],
      ],
    },
    modules: [
      { module_key: "temple", display_name: "Dashboard", frontend_path: "/temple/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Sevas", frontend_path: "/temple/sevas", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Donations", frontend_path: "/temple/donations", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Devotees", frontend_path: "/temple/devotees", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Public Payments", frontend_path: "/temple/public-payments", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Receipts", frontend_path: "/temple/receipts", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Reports", frontend_path: "/temple/reports", nav_group: "Administration", enabled: true },
      { module_key: "temple", display_name: "Panchang", frontend_path: "/temple/panchang", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Settings", frontend_path: "/temple/settings", nav_group: "Administration", enabled: true },
      { module_key: "audit", display_name: "Implementation Checks", frontend_path: "/temple/implementation-checks", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Platform Owners", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
    ],
  },
  gruha: {
    title: "GruhaMitra",
    subtitle: "Housing society operations with shared MitraBooks accounting",
    logo: "../assets/brand/gruhamitra-logo.png",
    video: "../assets/brand/gruhamitra-logo.mp4",
    theme: "gruha-theme",
    scopeTitle: "GruhaMitra Housing Workspace",
    scopeCopy: "Preserves the old housing layout pattern: dashboard, maintenance, members, complaints, reports, assets, and settings.",
    legacyTitle: "GruhaMitra layout mode",
    legacyCopy: "Housing-first navigation mirrors the old web app while using the unified shell.",
    dashboard: {
      type: "gruha",
      stats: [
        ["Society Balance", "Rs. 12.6L", "cash and bank"],
        ["This Month Billing", "Rs. 4.8L", "maintenance cycle"],
        ["Dues Pending", "Rs. 1.2L", "42 units"],
        ["Complaints Open", "18", "service desk"],
      ],
      actions: ["Accounting", "Generate Bills", "Members", "Find Society", "My Memberships", "Join Requests", "Complaints", "Reports", "Message", "Meeting", "Society Assets", "Settings"],
      activity: ["Maintenance collection posted", "New member approval pending", "Lift complaint assigned to vendor"],
      trend: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    },
    modules: [
      { module_key: "housing", display_name: "Dashboard", frontend_path: "/housing/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Maintenance", frontend_path: "/housing/maintenance", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Members", frontend_path: "/housing/members", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Complaints", frontend_path: "/housing/complaints", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "housing", display_name: "Reports", frontend_path: "/housing/reports", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Settings", frontend_path: "/housing/settings", nav_group: "Administration", enabled: true },
    ],
  },
};

let currentExperience = initialExperience();
let selectedOrgType = null;
let lastMandirReceipt = null;
let activeReceiptPreviewObjectUrl = "";
let activeMandirWorkspace = "overview";
let activePlatformWorkspace = "dashboard";
let lastPlatformOwnerDashboard = null;
let lastMandirPaymentAccounts = { cash_accounts: [], bank_accounts: [] };
let lastMandirAccounts = [];
let lastMandirFormResult = null;
let lastMandirPanchang = null;
let lastMandirOperationalReports = {};
let lastMandirModuleConfig = {};
let lastMandirComplianceConfig = { enable_80g: false, enable_fcra: false };
const todayForReports = new Date();
const firstDayForReports = new Date(todayForReports.getFullYear(), todayForReports.getMonth(), 1);
let accountingDrilldownState = {
  level: "month",
  from_date: firstDayForReports.toISOString().slice(0, 10),
  to_date: todayForReports.toISOString().slice(0, 10),
  month: "",
  week_start: "",
  day: "",
};
let lastAccountingDrilldown = null;
let lastAccountingVoucherDetail = null;
let lastBusinessParties = [];
let lastBusinessAccounts = [];
let coaTypeFilter = "";
let lastCaDocuments = [];
let lastCaDocumentsResult = null;
let lastCaClients = [];
let lastCaClientsResult = null;
let caAccessUsers = [];
let caAccessLoading = false;
let caInviteError = "";
let caInviteSuccess = "";
let caClientDraft = {
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
let caPracticeFilters = {
  status: "",
  client_name: "",
  assigned_to: "",
  priority: "",
};
const CA_DOCUMENT_WORKFLOW = ["uploaded", "under_review", "query_raised", "reviewed", "posted"];
const CA_DOCUMENT_LABELS = {
  uploaded: "Uploaded",
  under_review: "Under review",
  query_raised: "Query raised",
  reviewed: "Reviewed",
  posted: "Posted",
};
const CA_DOCUMENT_PRIORITY_LABELS = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

const appRoot = document.getElementById("app-root");
const brandLogo = document.getElementById("brand-logo");
const brandTitle = document.getElementById("brand-title");
const brandSubtitle = document.getElementById("brand-subtitle");
const topbarTitle = document.getElementById("topbar-title");
const topbarSubtitle = document.getElementById("topbar-subtitle");
const appKeyLabel = document.getElementById("app-key-label");
const sessionPill = document.getElementById("session-pill");
const loginStatus = document.getElementById("login-status");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const forgotPasswordForm = document.getElementById("forgot-password-form");
const forgotPasswordEmail = document.getElementById("forgot-email");
const resetPasswordForm = document.getElementById("reset-password-form");
const resetNewPasswordInput = document.getElementById("reset-new-password");
const resetConfirmPasswordInput = document.getElementById("reset-confirm-password");
const topbarCurrent = document.getElementById("topbar-current");
const topbarUser = document.getElementById("topbar-user");
const topbarAvatar = document.getElementById("topbar-avatar");
const scopeTitle = document.getElementById("scope-title");
const scopeCopy = document.getElementById("scope-copy");
const legacyTitle = document.getElementById("legacy-title");
const legacyCopy = document.getElementById("legacy-copy");
const legacyVideo = document.getElementById("legacy-video");
const legacyImage = document.getElementById("legacy-image");
const dashboardPreview = document.getElementById("dashboard-preview");
const nav = document.getElementById("nav");
const moduleList = document.getElementById("module-list");
const apiOutput = document.getElementById("api-output");
const healthPill = document.getElementById("health-pill");
const moduleState = document.getElementById("module-state");
const apiBaseInput = document.getElementById("api-base");
const tokenInput = document.getElementById("access-token");
const sidebarAvatar = document.getElementById("sidebar-avatar");
const sidebarUserName = document.getElementById("sidebar-user-name");
const sidebarUserRole = document.getElementById("sidebar-user-role");
const currentOrgType = document.getElementById("current-org-type");
const currentOrgTenant = document.getElementById("current-org-tenant");
const entitlementDialog = document.getElementById("entitlement-dialog");
const entitlementForm = document.getElementById("entitlement-form");
const entitlementTenantId = document.getElementById("entitlement-tenant-id");
const entitlementTenantLabel = document.getElementById("entitlement-tenant-label");
const entitlementPlan = document.getElementById("entitlement-plan");
const entitlementStatus = document.getElementById("entitlement-status");
const entitlementModules = document.getElementById("entitlement-modules");
const mandirVerificationDialog = document.getElementById("mandir-verification-dialog");
const mandirVerificationForm = document.getElementById("mandir-verification-form");
const mandirVerificationPaymentId = document.getElementById("mandir-verification-payment-id");
const mandirVerificationLabel = document.getElementById("mandir-verification-label");
const mandirVerificationUtr = document.getElementById("mandir-verification-utr");
const mandirVerificationDate = document.getElementById("mandir-verification-date");
const mandirVerificationBankAccount = document.getElementById("mandir-verification-bank-account");
const receiptPreviewDialog = document.getElementById("receipt-preview-dialog");
const receiptPreviewFrame = document.getElementById("receipt-preview-frame");
const receiptPreviewLabel = document.getElementById("receipt-preview-label");
const mandirCancelReceiptDialog = document.getElementById("mandir-cancel-receipt-dialog");
const mandirCancelReceiptForm = document.getElementById("mandir-cancel-receipt-form");
const mandirCancelReceiptUrl = document.getElementById("mandir-cancel-receipt-url");
const mandirCancelReceiptLabel = document.getElementById("mandir-cancel-receipt-label");
const mandirCancelReceiptReason = document.getElementById("mandir-cancel-receipt-reason");
const mandirCancelRefundMode = document.getElementById("mandir-cancel-refund-mode");
const mandirCancelRefundReference = document.getElementById("mandir-cancel-refund-reference");
const mandirCancelReceiptSubmit = document.getElementById("mandir-cancel-receipt-submit");
const mandirRejectionDialog = document.getElementById("mandir-rejection-dialog");
const mandirRejectionForm = document.getElementById("mandir-rejection-form");
const mandirRejectionPaymentId = document.getElementById("mandir-rejection-payment-id");
const mandirRejectionLabel = document.getElementById("mandir-rejection-label");
const mandirRejectionReason = document.getElementById("mandir-rejection-reason");
const mandirCorrectionDialog = document.getElementById("mandir-correction-dialog");
const mandirCorrectionForm = document.getElementById("mandir-correction-form");
const mandirCorrectionPaymentId = document.getElementById("mandir-correction-payment-id");
const mandirCorrectionLabel = document.getElementById("mandir-correction-label");
const mandirCorrectionAmount = document.getElementById("mandir-correction-amount");
const mandirCorrectionPhone = document.getElementById("mandir-correction-phone");
const mandirCorrectionType = document.getElementById("mandir-correction-type");
const mandirCorrectionPurpose = document.getElementById("mandir-correction-purpose");
const mandirSplash = document.getElementById("mandir-splash");
const mandirSplashVideo = document.getElementById("mandir-splash-video");
const mandirSplashImage = document.getElementById("mandir-splash-image");
const brandSplashCopy = document.getElementById("brand-splash-copy");
const topbarControlStrip = document.querySelector(".topbar-control-strip");
const accountMenuTrigger = document.getElementById("account-menu-trigger");
const accountMenuPanel = document.getElementById("account-menu-panel");
const passwordDialog = document.getElementById("change-password-dialog");
const passwordForm = document.getElementById("change-password-form");
const passwordStatus = document.getElementById("password-error-message");
const currentPasswordInput = document.getElementById("current-password");
const newPasswordInput = document.getElementById("new-password");
const confirmNewPasswordInput = document.getElementById("confirm-password");


// ══════════════════════════════════════════════════════════════════════
// SECTION: EXPERIENCE + MODULE CONFIG
// NOTE  : renderModules, mandirNavigationItems, gruhaNavigationItems, loadAndRenderGroupedNav
// ══════════════════════════════════════════════════════════════════════

function renderModules(modules = experienceConfig[currentExperience].modules, options = {}) {
  const config = experienceConfig[currentExperience];
  const preview = options.preview !== false;
  appRoot.className = `app ${config.theme} ${isProductionShell() ? "production-shell" : ""} ${isMandirHost() ? "mandir-domain" : ""}`.trim();
  updateSessionUi();
  updateTrustedContextUi();
  if (appKeyLabel) {
    appKeyLabel.textContent = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  }
  if (topbarTitle) {
    topbarTitle.textContent = currentExperience === "mandir" ? "MandirMitra Temple" : config.title;
  }
  if (topbarSubtitle) {
    topbarSubtitle.textContent = currentExperience === "mandir"
      ? "Temple / Trust Management & Accounting System"
      : config.subtitle;
  }
  if (topbarControlStrip) {
    topbarControlStrip.hidden = currentExperience !== "mitrabooks";
  }
  brandLogo.src = config.logo;
  brandLogo.alt = config.title;
  brandTitle.textContent = config.title;
  brandSubtitle.textContent = config.subtitle;
  scopeTitle.textContent = config.scopeTitle;
  scopeCopy.textContent = config.scopeCopy;
  legacyTitle.textContent = config.legacyTitle;
  legacyCopy.textContent = config.legacyCopy;
  legacyImage.src = config.logo;
  legacyImage.alt = config.title;
  if (config.video && getAccessToken()) {
    legacyVideo.src = config.video;
    legacyVideo.hidden = false;
    legacyImage.hidden = true;
    legacyVideo.play().catch(() => {});
  } else {
    legacyVideo.pause();
    legacyVideo.removeAttribute("src");
    legacyVideo.load();
    legacyVideo.hidden = true;
    legacyImage.hidden = false;
  }

  nav.innerHTML = "";
  moduleList.innerHTML = "";
  dashboardPreview.innerHTML = renderDashboardPreview(config);

  // On a fresh page load / refresh the dashboard overview must fetch its live
  // KPIs. The nav-click and org-select paths call this, but the boot render
  // (renderModules) did not — so a refresh showed Rs 0 until you navigated.
  if (hasTrustedSession() && currentExperience === "mitrabooks" && activeBusinessWorkspace === "overview"
      && activeOrgSelectorType() === "BUSINESS") {
    loadBusinessDashboardStats();
  }

  const navItems = currentExperience === "mandir"
    ? mandirNavigationItems()
    : currentExperience === "gruha"
      ? gruhaNavigationItems()
      : currentExperience === "mitrabooks"
        ? businessNavigationItems()
        : currentExperience === "platform"
          ? platformNavigationItems(modules)
        : modules.map((module) => ({
        label: `${module.nav_group || "Module"}: ${module.display_name}`,
        module,
        workspace: mandirWorkspaceFromModule(module),
        }));

  if (currentExperience === "mitrabooks") {
    renderGroupedNav(businessNavigationGroups());
  } else {
  navItems.forEach((item) => {
    const module = item.module || {};
    const link = document.createElement("a");
    link.href = "#";
    link.className = `${module.enabled === false ? "locked" : ""} ${item.child ? "child" : ""}`.trim();
    link.setAttribute("aria-disabled", module.enabled ? "false" : "true");
    link.dataset.moduleKey = module.module_key || "";
    link.dataset.frontendPath = module.frontend_path || "";
    const mandirWorkspace = item.workspace || mandirWorkspaceFromModule(module);
    if (mandirWorkspace) {
      link.dataset.mandirWorkspace = mandirWorkspace;
    }
    if (item.gruhaWorkspace) {
      link.dataset.gruhaWorkspace = item.gruhaWorkspace;
    }
    if (item.businessWorkspace) {
      link.dataset.businessWorkspace = item.businessWorkspace;
    }
    if (item.platformWorkspace) {
      link.dataset.platformWorkspace = item.platformWorkspace;
    }
    link.dataset.navIcon = item.icon || navIconForMandirWorkspace(mandirWorkspace);
    link.textContent = item.label;
    nav.appendChild(link);
  });
  }

  modules.forEach((module) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${escapeHtml(module.display_name)}</strong>
      <span class="muted">${escapeHtml(module.module_key)} -> ${escapeHtml(module.frontend_path || "no frontend path yet")}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : preview ? "preview only" : "available or planned"}</span>
    `;
    moduleList.appendChild(item);
  });
  syncMandirNavActiveState();
  syncGruhaNavActiveState();
  syncPlatformNavActiveState();
  syncBusinessNavActiveState();
}

function mandirNavigationItems() {
  return [
    { label: "Dashboard", workspace: "overview", icon: "▦", module: { module_key: "temple", frontend_path: "/temple/dashboard", enabled: true } },
    { label: "Sevas", workspace: "sevas", icon: "♜", module: { module_key: "temple", frontend_path: "/temple/sevas", enabled: true } },
    { label: "Book Sevas", workspace: "book-sevas", icon: "♜", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/book", enabled: true } },
    { label: "Seva Bookings / Reschedule", workspace: "seva-bookings", icon: "▤", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/bookings", enabled: true } },
    { label: "Seva Management", workspace: "seva-management", icon: "▤", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/manage", enabled: true } },
    { label: "Reschedule Approval", workspace: "reschedule-approval", icon: "✓", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/reschedule", enabled: true } },
    { label: "Donations", workspace: "donations", icon: "▰", module: { module_key: "temple", frontend_path: "/temple/donations", enabled: true } },
    { label: "Devotees", workspace: "devotees", icon: "●●", module: { module_key: "temple", frontend_path: "/temple/devotees", enabled: true } },
    { label: "Public Payments", workspace: "payments", icon: "▣", module: { module_key: "temple", frontend_path: "/temple/public-payments", enabled: true } },
    { label: "Payment Exceptions", workspace: "exceptions", icon: "!", child: true, module: { module_key: "temple", frontend_path: "/temple/payment-exceptions", enabled: true } },
    { label: "Receipts", workspace: "receipts", icon: "▤", module: { module_key: "temple", frontend_path: "/temple/receipts", enabled: true } },
    { label: "Reports", workspace: "reports", icon: "▥", module: { module_key: "audit", frontend_path: "/temple/reports", enabled: true } },
    { label: "Panchang", workspace: "panchang", icon: "□", module: { module_key: "temple", frontend_path: "/temple/panchang", enabled: true } },
    { label: "Settings", workspace: "settings", icon: "⚙", module: { module_key: "temple", frontend_path: "/temple/settings", enabled: true } },
    { label: "Implementation Checks", workspace: "implementation", icon: "☑", module: { module_key: "audit", frontend_path: "/temple/implementation-checks", enabled: true } },
    { label: "Platform Owners", workspace: "platform-owners", icon: "♜", module: { module_key: "platform_owner", frontend_path: "/platform-owner/dashboard", enabled: true } },
    { label: "Accounting", workspace: "accounting", icon: "▣", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
    { label: "Chart of Accounts", workspace: "accounting", icon: "▥", child: true, module: { module_key: "accounting", frontend_path: "/accounting/accounts", enabled: true } },
    { label: "Quick Expense", workspace: "accounting", icon: "₹", child: true, module: { module_key: "accounting", frontend_path: "/accounting/expenses", enabled: true } },
    { label: "Journal Entries", workspace: "accounting", icon: "▤", child: true, module: { module_key: "accounting", frontend_path: "/accounting/journals", enabled: true } },
    { label: "Bank Reconciliation", workspace: "accounting", icon: "▰", child: true, module: { module_key: "accounting", frontend_path: "/accounting/bank", enabled: true } },
    { label: "Financial Closing", workspace: "accounting", icon: "▣", child: true, module: { module_key: "accounting", frontend_path: "/accounting/closing", enabled: true } },
    { label: "UPI Payments", workspace: "payments", icon: "▭", child: true, module: { module_key: "temple", frontend_path: "/temple/upi-payments", enabled: true } },
    { label: "Accounting Reports", workspace: "accounting", icon: "▥", child: true, module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: true } },
  ];
}

function gruhaNavigationItems() {
  return [
    { label: "Dashboard", gruhaWorkspace: "overview", icon: "D", module: { module_key: "housing", frontend_path: "/housing/dashboard", enabled: true } },
    { label: "Maintenance", gruhaWorkspace: "maintenance", icon: "M", module: { module_key: "housing", frontend_path: "/housing/maintenance", enabled: true } },
    { label: "Members", gruhaWorkspace: "members", icon: "U", module: { module_key: "housing", frontend_path: "/housing/members", enabled: true } },
    { label: "Flats", gruhaWorkspace: "flats", icon: "F", child: true, module: { module_key: "housing", frontend_path: "/housing/flats", enabled: true } },
    { label: "Complaints", gruhaWorkspace: "complaints", icon: "C", module: { module_key: "housing", frontend_path: "/housing/complaints", enabled: true } },
    { label: "Messages", gruhaWorkspace: "messages", icon: "N", module: { module_key: "housing", frontend_path: "/housing/messages", enabled: true } },
    { label: "Meetings", gruhaWorkspace: "meetings", icon: "G", module: { module_key: "housing", frontend_path: "/housing/meetings", enabled: true } },
    { label: "Assets", gruhaWorkspace: "assets", icon: "A", module: { module_key: "housing", frontend_path: "/housing/assets", enabled: true } },
    { label: "Accounting", gruhaWorkspace: "accounting", icon: "L", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
    { label: "Reports", gruhaWorkspace: "reports", icon: "R", module: { module_key: "housing", frontend_path: "/housing/reports", enabled: true } },
    { label: "Settings", gruhaWorkspace: "settings", icon: "S", module: { module_key: "audit", frontend_path: "/housing/settings", enabled: true } },
  ];
}

function platformNavigationItems(modules = experienceConfig.platform.modules) {
  return modules.map((module) => ({
    label: `${module.nav_group || "Platform"}: ${module.display_name}`,
    platformWorkspace: platformWorkspaceFromModule(module),
    module,
  }));
}

function legacyBusinessNavigationItems() {
  return [
    { label: "Dashboard", businessWorkspace: "overview", icon: "▦", module: { module_key: "business", frontend_path: "/business", enabled: true } },
    { label: "Parties", businessWorkspace: "parties", icon: "●", module: { module_key: "business", frontend_path: "/business/parties", enabled: true } },
    { label: "Vouchers", businessWorkspace: "vouchers", icon: "▤", module: { module_key: "business", frontend_path: "/business/vouchers", enabled: true } },
    { label: "Audit Trail", businessWorkspace: "audit", icon: "⏱", module: { module_key: "audit", frontend_path: "/audit", enabled: true } },
    { label: "Accounting", businessWorkspace: "accounting", icon: "▣", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
  ];
}

/**
 * Load grouped navigation from /api/v1/modules/me (Phase 1D)
 * Groups modules by nav_group for professional accounting app layout
 */
async function loadAndRenderGroupedNav(appKey) {
  console.log("[Nav] loadAndRenderGroupedNav called with appKey:", appKey);

  if (appKey === "mitrabooks") {
    console.log("[Nav] Using hardcoded MitraBooks navigation");
    const groups = businessNavigationGroups();
    console.log("[Nav] businessNavigationGroups returned", groups.length, "groups");
    console.log("[Nav] Groups:", groups.map(g => g.name));
    renderGroupedNav(groups);
    console.log("[Nav] renderGroupedNav completed");
    return;
  }
  try {
    const response = await loadModules(appKey);
    if (!response.ok) {
      console.log("[Nav] API returned status", response.status, "- using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    const payload = response.payload || {};
    const modules = payload.enabled_modules || [];

    if (!Array.isArray(modules) || modules.length === 0) {
      console.log("[Nav] No modules in response - using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    console.log("[Nav] Loaded", modules.length, "modules from API");

    // Group modules by nav_group field
    const grouped = {};
    const groupOrder = [
      "Main Workspaces",
      "Core Ledger",
      "Income (Sales)",
      "Expenses (Purchases)",
      "Banking & Treasury",
      "Taxes & Compliance",
      "Intelligence & Reports",
      "Configuration & Extensions",
    ];

    modules.forEach(module => {
      const group = module.nav_group || "Modules";
      if (!grouped[group]) {
        grouped[group] = [];
      }
      grouped[group].push({
        label: module.display_name,
        businessWorkspace: module.frontend_path?.split("/").pop() || "default",
        icon: module.icon || "●",
        module: {
          module_key: module.module_key,
          frontend_path: module.frontend_path,
          enabled: module.enabled !== false,
          display_name: module.display_name,
        },
      });
    });

    // Sort groups by predefined order
    const sortedGroups = [];
    groupOrder.forEach(group => {
      if (grouped[group]) {
        sortedGroups.push({ name: group, items: grouped[group] });
      }
    });

    // Add remaining groups not in predefined order
    Object.keys(grouped).forEach(group => {
      if (!groupOrder.includes(group)) {
        sortedGroups.push({ name: group, items: grouped[group] });
      }
    });

    if (sortedGroups.length === 0) {
      console.log("[Nav] No groups created - using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    renderGroupedNav(sortedGroups);
    console.log("[Nav] Rendered grouped navigation with", sortedGroups.length, "groups");
  } catch (error) {
    console.error("[Nav] Error loading grouped navigation:", error);
    renderGroupedNavFromItems(businessNavigationItems());
  }
}

/**
 * Render navigation with group headers (Phase 1D)
 */

// ══════════════════════════════════════════════════════════════════════
// SECTION: NAVIGATION RENDERING
// NOTE  : renderGroupedNav, renderGroupedNavFromItems — builds sidebar from nav group config
// ══════════════════════════════════════════════════════════════════════

function renderGroupedNav(groups) {
  console.log("[Nav] renderGroupedNav called with", groups.length, "groups");
  const nav = document.getElementById("nav");
  if (!nav) {
    console.error("[Nav] ERROR: nav element not found in DOM!");
    return;
  }

  console.log("[Nav] Found nav element, clearing and populating...");
  nav.innerHTML = "";

  groups.forEach((group, groupIndex) => {
    // Hide not-yet-built items (enabled:false roadmap stubs) so the sidebar shows
    // only working features. Config is left intact — flip a stub to enabled:true
    // when it ships and it reappears. Groups with nothing built are skipped.
    const visibleItems = group.items.filter((item) => item.module.enabled !== false);
    if (visibleItems.length === 0) return;

    const groupId = `business-nav-group-${groupIndex}`;
    const header = document.createElement("button");
    header.className = "nav-group-toggle";
    header.type = "button";
    header.dataset.navGroupToggle = groupId;
    header.setAttribute("aria-expanded", "true");
    header.setAttribute("aria-controls", groupId);
    header.innerHTML = `<span>${escapeHtml(group.name)}</span><span aria-hidden="true">v</span>`;
    nav.appendChild(header);

    const panel = document.createElement("div");
    panel.className = "nav-group-items";
    panel.id = groupId;
    panel.dataset.navGroupItems = groupId;
    visibleItems.forEach(item => {
      const link = document.createElement("a");
      link.href = "#";
      link.className = item.module.enabled ? "erp-nav-link" : "erp-nav-link locked";
      link.setAttribute("aria-disabled", item.module.enabled ? "false" : "true");
      link.dataset.moduleKey = item.module.module_key || "";
      link.dataset.frontendPath = item.module.frontend_path || "";
      link.dataset.businessWorkspace = item.businessWorkspace || "";
      link.dataset.navIcon = item.icon;
      link.innerHTML = `
        <span class="nav-icon">${escapeHtml(item.icon || "")}</span>
        <span class="nav-label">${escapeHtml(item.label)}</span>
        ${item.badge ? `<span class="nav-badge">${escapeHtml(item.badge)}</span>` : ""}
      `;
      panel.appendChild(link);
    });
    nav.appendChild(panel);
  });

  syncBusinessNavActiveState();
}

/**
 * Fallback: Render hardcoded navigation items (no grouping, while backend adds nav_group)
 */
function renderGroupedNavFromItems(items) {
  const nav = document.getElementById("nav");
  if (!nav) return;

  nav.innerHTML = "";
  console.log("[Nav] Using fallback with", items.length, "hardcoded items");

  // Add a single "Main" group header for fallback
  const header = document.createElement("div");
  header.className = "nav-group-header";
  header.textContent = "Main";
  header.style.cssText = `
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted, #94a3b8);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px 8px;
    margin-top: 0;
  `;
  nav.appendChild(header);

  items.forEach(item => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = item.module.enabled === false ? "locked" : "";
    link.setAttribute("aria-disabled", item.module.enabled ? "false" : "true");
    link.dataset.moduleKey = item.module.module_key || "";
    link.dataset.frontendPath = item.module.frontend_path || "";
    link.dataset.businessWorkspace = item.businessWorkspace || "";
    link.dataset.navIcon = item.icon;
    link.textContent = item.label;
    nav.appendChild(link);
    console.log("[Nav]   - Main:", item.label);
  });

  syncBusinessNavActiveState();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: STAT CARDS + ACTIVITY + RECENT VOUCHERS
// NOTE  : renderStatCards, renderActionTiles, renderActivity, renderBusinessRecentVoucherRows
// ══════════════════════════════════════════════════════════════════════

function renderStatCards(stats) {
  return stats.map(([label, value, subtext]) => `
    <article class="metric-tile">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${subtext}</small>
    </article>
  `).join("");
}

function renderActionTiles(actions) {
  return actions.map((action) => `
    <button class="quick-tile" type="button">
      <span class="quick-icon">${action.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span>
      <span>${action}</span>
    </button>
  `).join("");
}

function renderActivity(items) {
  return items.map((item) => `<li><span class="activity-dot"></span><span>${item}</span></li>`).join("");
}

function renderBusinessRecentVoucherRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state compact">
        <strong>No posted vouchers yet</strong>
        <span>Post the first balanced journal to start the operational timeline.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table business-recent-table">
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Date</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 5).map((row) => {
            const status = String(row.status || "posted");
            const isReversed = status === "reversed";
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(row.reference || row.cheque_number || "-")}</strong>
                  <span class="row-subtext">${escapeHtml((row.description || row.narration || "").slice(0, 42))}</span>
                </td>
                <td>${escapeHtml(String(row.entry_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.voucher_type || "journal")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit || row.amount || 0))}</td>
                <td><span class="pill ${isReversed ? "warn" : "ok"}">${escapeHtml(status)}</span></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: CA PRACTICE PORTAL + DOCUMENT INTAKE
// API   : GET/POST /api/v1/business/ca-documents
// NOTE  : renderCaDocumentTable, renderCaDocumentIntake, caPracticeSummary
// ══════════════════════════════════════════════════════════════════════

function caDocumentStatusLabel(status) {
  return CA_DOCUMENT_LABELS[status] || String(status || "Uploaded");
}

function nextCaDocumentStatus(status) {
  const index = CA_DOCUMENT_WORKFLOW.indexOf(status || "uploaded");
  if (index < 0 || index >= CA_DOCUMENT_WORKFLOW.length - 1) {
    return "";
  }
  return CA_DOCUMENT_WORKFLOW[index + 1];
}

function caDocumentMetrics(rows) {
  const counts = CA_DOCUMENT_WORKFLOW.reduce((acc, status) => {
    acc[status] = 0;
    return acc;
  }, {});
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const status = row.status || "uploaded";
    counts[status] = (counts[status] || 0) + 1;
  });
  return [
    ["Uploaded", String(counts.uploaded || 0), "Awaiting classification"],
    ["Under review", String(counts.under_review || 0), "Staff review in progress"],
    ["Reviewed", String(counts.reviewed || 0), "Ready for posting"],
    ["Posted", String(counts.posted || 0), "Linked to vouchers or returns"],
    ["Query raised", String(counts.query_raised || 0), "Needs client clarification"],
  ];
}

function caDocumentPriorityLabel(priority) {
  return CA_DOCUMENT_PRIORITY_LABELS[priority] || "Normal";
}

function caPracticeSummary(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const clients = new Set();
  const assignees = new Map();
  const compliance = new Map();
  let clientAccess = 0;
  let urgent = 0;
  safeRows.forEach((row) => {
    if (row.client_name) {
      clients.add(row.client_name);
    }
    const owner = row.assigned_to || "Unassigned";
    assignees.set(owner, (assignees.get(owner) || 0) + 1);
    const area = row.compliance_area || "General";
    compliance.set(area, (compliance.get(area) || 0) + 1);
    if (row.client_access_enabled) {
      clientAccess += 1;
    }
    if (row.priority === "urgent" || row.priority === "high") {
      urgent += 1;
    }
  });
  return {
    clientCount: clients.size,
    clientAccess,
    urgent,
    assignees: Array.from(assignees.entries()).sort((a, b) => b[1] - a[1]),
    compliance: Array.from(compliance.entries()).sort((a, b) => b[1] - a[1]),
  };
}

function caClientComplianceLabel(tracks) {
  const items = Array.isArray(tracks) ? tracks.filter(Boolean) : [];
  return items.length ? items.join(", ") : "General";
}

function caClientSwitchRows() {
  if (Array.isArray(lastCaClients) && lastCaClients.length) {
    return lastCaClients
      .filter((row) => row.active !== false)
      .map((row) => ({
        client: row.client_name || "Unnamed client",
        count: lastCaDocuments.filter((doc) => (doc.client_name || "") === (row.client_name || "")).length,
        owner: row.client_owner || "",
        access_level: row.access_level || "view_only",
        compliance: caClientComplianceLabel(row.compliance_tracks),
      }));
  }
  return caPracticeClientBreakdown(lastCaDocuments);
}

function caClientById(clientId) {
  return (Array.isArray(lastCaClients) ? lastCaClients : [])
    .find((row) => String(row.client_id || "") === String(clientId || "")) || null;
}

function caPracticeClientBreakdown(rows) {
  const counts = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const key = String(row.client_name || "Unassigned client").trim() || "Unassigned client";
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([client, count]) => ({ client, count }));
}

let caDocumentAttachmentState = {
  document_id: "",
  client_name: "",
  items: [],
  loading: false,
};

function buildFrontendApiUrl(path) {
  const baseUrl = String(getConfiguredApiBaseUrl() || "").trim().replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (baseUrl === "/api" && normalizedPath.startsWith("/api/")) {
    return normalizedPath;
  }
  if (baseUrl.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${baseUrl.slice(0, -4)}${normalizedPath}`;
  }
  return `${baseUrl}${normalizedPath}`;
}

function businessAttachmentPath(ownerType, ownerId, attachmentId = "") {
  const safeOwnerId = encodeURIComponent(ownerId || "");
  if (ownerType === "sales_invoice") {
    return attachmentId
      ? `/api/v1/business/invoices/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
      : `/api/v1/business/invoices/${safeOwnerId}/attachments`;
  }
  if (ownerType === "purchase_bill") {
    return attachmentId
      ? `/api/v1/business/bills/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
      : `/api/v1/business/bills/${safeOwnerId}/attachments`;
  }
  return attachmentId
    ? `/api/v1/business/ca-documents/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
    : `/api/v1/business/ca-documents/${safeOwnerId}/attachments`;
}

async function uploadBusinessAttachmentFiles(ownerType, ownerId, files) {
  const queue = Array.from(files || []).filter(Boolean);
  const results = [];
  for (const file of queue) {
    const headers = { "X-App-Key": "mitrabooks" };
    const token = getAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(buildFrontendApiUrl(businessAttachmentPath(ownerType, ownerId)), {
        method: "POST",
        headers,
        body: formData,
      });
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json") ? await response.json() : await response.text();
      results.push({ ok: response.ok, status: response.status, payload });
    } catch (error) {
      results.push({
        ok: false,
        status: 0,
        payload: { detail: error instanceof Error ? error.message : "Attachment upload failed" },
      });
    }
  }
  return results;
}

async function listBusinessAttachments(ownerType, ownerId) {
  return apiRequest("mitrabooks", `${businessAttachmentPath(ownerType, ownerId)}?limit=100`, { method: "GET" });
}

function attachmentListSummary(items) {
  return Array.isArray(items) ? `${items.length} file(s)` : "0 file(s)";
}

function renderBusinessAttachmentPanel({ ownerType, ownerId, items, loading, title, emptyCopy, uploadButtonLabel }) {
  const safeItems = Array.isArray(items) ? items : [];
  return `
    <div class="verification-panel" data-attachment-panel="${escapeHtml(ownerType)}">
      <div class="preview-heading compact">
        <div>
          <h5>${escapeHtml(title)}</h5>
          <p>${loading ? "Loading attachments…" : `${attachmentListSummary(safeItems)} for this document.`}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="refresh-attachments" data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">Refresh</button>
        </div>
      </div>
      <div class="ca-document-actions">
        <input type="file" multiple data-attachment-input data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">
        <button type="button" data-business-action="upload-attachments" data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">${escapeHtml(uploadButtonLabel || "Upload files")}</button>
      </div>
      ${safeItems.length ? `
        <div class="table-preview compact-table erp-table">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Type</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${safeItems.map((item) => `
                <tr>
                  <td>${escapeHtml(item.file_name || "attachment")}</td>
                  <td>${escapeHtml(item.content_type || "application/octet-stream")}</td>
                  <td>${escapeHtml(String(item.size_bytes || 0))} bytes</td>
                  <td>${escapeHtml(String(item.uploaded_at || "").slice(0, 10) || "-")}</td>
                  <td>
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="download-attachment"
                      data-owner-type="${escapeHtml(ownerType)}"
                      data-owner-id="${escapeHtml(ownerId || "")}"
                      data-attachment-id="${escapeHtml(item.attachment_id || "")}"
                      data-file-name="${escapeHtml(item.file_name || "attachment")}"
                    >Download</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state compact">
          <strong>No attachments yet</strong>
          <span>${escapeHtml(emptyCopy)}</span>
        </div>
      `}
    </div>
  `;
}

function renderCaPracticeFilters() {
  return `
    <form class="ca-practice-filter-panel" data-ca-filter-form>
      <label>
        <span>Status</span>
        <select name="status">
          <option value="">All statuses</option>
          ${CA_DOCUMENT_WORKFLOW.map((status) => `
            <option value="${escapeHtml(status)}" ${caPracticeFilters.status === status ? "selected" : ""}>${escapeHtml(caDocumentStatusLabel(status))}</option>
          `).join("")}
        </select>
      </label>
      <label>
        <span>Client</span>
        <input name="client_name" type="search" maxlength="160" value="${escapeHtml(caPracticeFilters.client_name)}" placeholder="Client or company">
      </label>
      <label>
        <span>Assigned to</span>
        <input name="assigned_to" type="search" maxlength="120" value="${escapeHtml(caPracticeFilters.assigned_to)}" placeholder="Staff or partner">
      </label>
      <label>
        <span>Priority</span>
        <select name="priority">
          <option value="">All priorities</option>
          ${Object.entries(CA_DOCUMENT_PRIORITY_LABELS).map(([value, label]) => `
            <option value="${escapeHtml(value)}" ${caPracticeFilters.priority === value ? "selected" : ""}>${escapeHtml(label)}</option>
          `).join("")}
        </select>
      </label>
      <div class="ca-practice-filter-actions">
        <button type="submit" class="secondary">Apply Filters</button>
        <button type="button" class="secondary" data-business-action="ca-doc-clear-filters">Clear</button>
      </div>
    </form>
  `;
}

function renderCaClientMaster() {
  const rows = Array.isArray(lastCaClients) ? lastCaClients : [];
  return `
    <section class="erp-panel" style="margin-bottom:1rem">
      <div class="preview-heading compact" style="margin-bottom:1rem">
        <div>
          <h5>Client Master</h5>
          <p>Tenant-scoped client/company records for CA practice access, assignment, and compliance routing.</p>
        </div>
      </div>
      <form data-ca-client-form class="ca-practice-filter-panel" style="margin-bottom:1rem">
        <label>
          <span>Client name</span>
          <input name="client_name" type="text" maxlength="160" value="${escapeHtml(caClientDraft.client_name)}" placeholder="Client book or company name" required>
        </label>
        <label>
          <span>GSTIN</span>
          <input name="gstin" type="text" maxlength="20" value="${escapeHtml(caClientDraft.gstin)}" placeholder="Optional GSTIN">
        </label>
        <label>
          <span>PAN</span>
          <input name="pan" type="text" maxlength="20" value="${escapeHtml(caClientDraft.pan)}" placeholder="Optional PAN">
        </label>
        <label>
          <span>Contact person</span>
          <input name="contact_person" type="text" maxlength="120" value="${escapeHtml(caClientDraft.contact_person)}" placeholder="Owner or finance contact">
        </label>
        <label>
          <span>Assigned to</span>
          <input name="assigned_to" type="text" maxlength="120" value="${escapeHtml(caClientDraft.assigned_to)}" placeholder="Reviewer or staff">
        </label>
        <label>
          <span>Client owner</span>
          <input name="client_owner" type="text" maxlength="120" value="${escapeHtml(caClientDraft.client_owner)}" placeholder="Partner or manager">
        </label>
        <label>
          <span>Engagement type</span>
          <input name="engagement_type" type="text" maxlength="80" value="${escapeHtml(caClientDraft.engagement_type)}" placeholder="Bookkeeping / GST / Audit">
        </label>
        <label>
          <span>Access level</span>
          <select name="access_level">
            <option value="view_only" ${caClientDraft.access_level === "view_only" ? "selected" : ""}>View only</option>
            <option value="data_entry" ${caClientDraft.access_level === "data_entry" ? "selected" : ""}>Data entry</option>
            <option value="full_access" ${caClientDraft.access_level === "full_access" ? "selected" : ""}>Full access</option>
            <option value="restricted_filing" ${caClientDraft.access_level === "restricted_filing" ? "selected" : ""}>Restricted filing</option>
          </select>
        </label>
        <label>
          <span>Compliance tracks</span>
          <input name="compliance_tracks" type="text" maxlength="240" value="${escapeHtml(caClientDraft.compliance_tracks)}" placeholder="GST, TDS, Audit">
        </label>
        <label>
          <span>Notes</span>
          <input name="notes" type="text" maxlength="500" value="${escapeHtml(caClientDraft.notes)}" placeholder="Optional notes">
        </label>
        <div class="ca-practice-filter-actions">
          <button type="submit">Add Client</button>
          <button type="button" class="secondary" data-business-action="ca-client-refresh">Refresh</button>
        </div>
      </form>
      ${rows.length ? `
        <div class="table-preview compact-table erp-table">
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Contact</th>
                <th>Owner / Staff</th>
                <th>Access</th>
                <th>Compliance</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((row) => `
                <tr>
                  <td>
                    <strong>${escapeHtml(row.client_name || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.engagement_type || "General engagement")}</span>
                  </td>
                  <td>
                    <strong>${escapeHtml(row.contact_person || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.gstin || row.pan || "No GSTIN/PAN")}</span>
                  </td>
                  <td>
                    <strong>${escapeHtml(row.client_owner || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.assigned_to || "Unassigned")}</span>
                  </td>
                  <td><span class="pill">${escapeHtml(String(row.access_level || "view_only").replaceAll("_", " "))}</span></td>
                  <td>${escapeHtml(caClientComplianceLabel(row.compliance_tracks))}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state compact">
          <strong>No CA client records yet</strong>
          <span>Create client books here, then use the review queue below for document operations.</span>
        </div>
      `}
    </section>
  `;
}

function renderCaPracticeOperations(rows) {
  const summary = caPracticeSummary(rows);
  const assigneeRows = summary.assignees.length ? summary.assignees : [["Unassigned", 0]];
  const complianceRows = summary.compliance.length ? summary.compliance : [["General", 0]];
  return `
    <div class="ca-practice-operations-grid">
      <article>
        <span>Client Tracking</span>
        <strong>${escapeHtml(String(summary.clientCount))}</strong>
        <small>Client books represented in this tenant queue.</small>
      </article>
      <article>
        <span>Client Access</span>
        <strong>${escapeHtml(String(summary.clientAccess))}</strong>
        <small>Metadata records flagged for client visibility when access rules are enabled.</small>
      </article>
      <article>
        <span>Priority Work</span>
        <strong>${escapeHtml(String(summary.urgent))}</strong>
        <small>High or urgent records needing staff attention.</small>
      </article>
    </div>
    <div class="ca-practice-workload-grid">
      <section>
        <h5>Staff Assignment</h5>
        ${assigneeRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
      <section>
        <h5>Compliance Dashboard</h5>
        ${complianceRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
    </div>
  `;
}

function renderCaDocumentTable(rows) {
  if (!lastCaDocumentsResult) {
    return `
      <div class="empty-state">
        <strong>Loading document metadata</strong>
        <span>Tenant-scoped CA practice records will appear here.</span>
      </div>
    `;
  }
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No CA document metadata yet</strong>
        <span>Add a client document record and upload supporting files into the tenant-scoped review queue.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table ca-document-status-table">
      <table>
        <thead>
          <tr>
            <th>Client</th>
            <th>Document type</th>
            <th>Period</th>
            <th>Owner / Staff</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Next action</th>
            <th>Posting ref</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const nextStatus = nextCaDocumentStatus(row.status);
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(row.client_name || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.original_file_name || "No file uploaded")}</span>
                  <span class="row-subtext">Book ${escapeHtml(row.book_id || row.accounting_entity_id || "primary")}${row.client_id ? ` | Client ${escapeHtml(row.client_id)}` : ""}</span>
                </td>
                <td>${escapeHtml(row.document_type || "-")}</td>
                <td>${escapeHtml(row.period || "-")}</td>
                <td>
                  <strong>${escapeHtml(row.client_owner || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.assigned_to || "Unassigned")}</span>
                </td>
                <td>
                  <span class="pill ${row.priority === "urgent" || row.priority === "high" ? "warn" : ""}">${escapeHtml(caDocumentPriorityLabel(row.priority))}</span>
                  <span class="row-subtext">${escapeHtml(row.due_date || "No due date")}</span>
                </td>
                <td><span class="pill">${escapeHtml(caDocumentStatusLabel(row.status))}</span></td>
                <td>
                  ${escapeHtml(row.next_action || "-")}
                  <span class="row-subtext">${escapeHtml(row.compliance_area || "General")} ${row.client_access_enabled ? " | Client access flagged" : ""}</span>
                  <span class="row-subtext">${escapeHtml(String(row.attachment_count || 0))} attachment(s)${row.reviewed_at ? ` | Reviewed ${escapeHtml(String(row.reviewed_at).slice(0, 10))}` : ""}</span>
                </td>
                <td>${escapeHtml(row.posting_reference || "-")}</td>
                <td>
                  <div class="invoice-detail-actions">
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="ca-doc-files"
                      data-document-id="${escapeHtml(row.document_id || "")}"
                      data-client-name="${escapeHtml(row.client_name || "")}"
                    >Files</button>
                    ${nextStatus ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="ca-doc-status"
                        data-document-id="${escapeHtml(row.document_id || "")}"
                        data-status="${escapeHtml(nextStatus)}"
                      >${escapeHtml(caDocumentStatusLabel(nextStatus))}</button>
                    ` : `<button class="secondary" type="button" disabled>Posted</button>`}
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderCaDocumentIntake(documentIntake) {
  const metrics = caDocumentMetrics(lastCaDocuments);
  return `
    <div class="ca-document-intake">
      <div class="ca-document-upload-card">
        <form data-ca-document-form>
          <span class="workbench-kicker">Document Metadata</span>
          <h4>${escapeHtml(documentIntake.title)}</h4>
          <p>${escapeHtml(documentIntake.copy)}</p>
          <div class="ca-upload-field-grid">
            <label>
              <span>Client book</span>
              <select name="client_id">
                <option value="">Manual client name</option>
                ${(Array.isArray(lastCaClients) ? lastCaClients : []).filter((row) => row.active !== false).map((row) => `
                  <option value="${escapeHtml(row.client_id || "")}">${escapeHtml(row.client_name || row.client_id || "")} | ${escapeHtml(row.accounting_entity_id || "primary")}</option>
                `).join("")}
              </select>
            </label>
            <label>
              <span>Client</span>
              <input name="client_name" type="text" maxlength="160" placeholder="Client book or company name" list="ca-client-name-options" required>
            </label>
            <label>
              <span>Document type</span>
              <select name="document_type" required>
                <option value="">Select type</option>
                <option>Bank statement</option>
                <option>Purchase bills</option>
                <option>Sales invoices</option>
                <option>GST return</option>
                <option>TDS file</option>
                <option>Supporting document</option>
              </select>
            </label>
            <label>
              <span>Period</span>
              <input name="period" type="text" maxlength="80" placeholder="May 2026 / FY 2026-27" required>
            </label>
            <label>
              <span>Assigned to</span>
              <input name="assigned_to" type="text" maxlength="120" placeholder="Reviewer or partner">
            </label>
            <label>
              <span>Client owner</span>
              <input name="client_owner" type="text" maxlength="120" placeholder="Partner or manager">
            </label>
            <label>
              <span>Priority</span>
              <select name="priority">
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
                <option value="low">Low</option>
              </select>
            </label>
            <label>
              <span>Due date</span>
              <input name="due_date" type="date">
            </label>
            <label>
              <span>Compliance area</span>
              <select name="compliance_area">
                <option value="">General</option>
                <option>GST</option>
                <option>TDS</option>
                <option>Income tax</option>
                <option>Audit</option>
                <option>ROC</option>
                <option>Bookkeeping</option>
              </select>
            </label>
            <label>
              <span>Original file name</span>
              <input name="original_file_name" type="text" maxlength="240" placeholder="Optional override for the first uploaded file">
            </label>
            <label>
              <span>Notes</span>
              <input name="notes" type="text" maxlength="500" placeholder="Review notes or client instruction">
            </label>
            <label>
              <span>Attachments</span>
              <input name="ca_attachments" type="file" multiple>
            </label>
            <label class="ca-checkbox-field">
              <input name="client_access_enabled" type="checkbox" value="true">
              <span>Flag for future client access</span>
            </label>
          </div>
          <div class="ca-document-actions">
            <button type="submit">Add Document Metadata</button>
            <button class="secondary" type="button" data-business-action="ca-doc-refresh">Refresh</button>
          </div>
          <datalist id="ca-client-name-options">
            ${(Array.isArray(lastCaClients) ? lastCaClients : []).map((row) => `
              <option value="${escapeHtml(row.client_name || "")}"></option>
            `).join("")}
          </datalist>
        </form>
      </div>

      <div class="ca-document-workflow" aria-label="Document review workflow">
        ${CA_DOCUMENT_WORKFLOW.map((status, index) => `
          <span class="${index === 0 ? "active" : ""}">${escapeHtml(caDocumentStatusLabel(status))}</span>
        `).join("")}
      </div>

      <div class="ca-document-status-grid">
        ${metrics.map(([label, value, copy]) => `
          <article>
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(copy)}</small>
          </article>
        `).join("")}
      </div>

      ${renderCaPracticeFilters()}
      ${renderCaPracticeOperations(lastCaDocuments)}

      ${renderCaDocumentTable(lastCaDocuments)}
      ${caDocumentAttachmentState.document_id ? renderBusinessAttachmentPanel({
        ownerType: "ca_document",
        ownerId: caDocumentAttachmentState.document_id,
        items: caDocumentAttachmentState.items,
        loading: caDocumentAttachmentState.loading,
        title: `CA document files${caDocumentAttachmentState.client_name ? ` · ${caDocumentAttachmentState.client_name}` : ""}`,
        emptyCopy: "Upload client source documents, statements, or review papers for this CA record.",
        uploadButtonLabel: "Upload files",
      }) : ""}

      <div class="ca-document-note">
        Current state: metadata records and supporting files are tenant-scoped and stored through the MitraBooks business API. Deferred scope: OCR, voucher posting, and return filing links are not enabled yet.
      </div>
    </div>
  `;
}

function plannedOrgWorkspaceModel(orgType) {
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

function renderSelectedOrgWorkspace() {
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

let businessDashboardLoadInFlight = false;
let businessMisLoadInFlight = false;


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS EXECUTIVE DASHBOARD
// API   : GET /api/v1/business/dashboard/stats
// NOTE  : renderBusinessExecutiveDashboard — KPI cards, quick actions, MIS panel
// ══════════════════════════════════════════════════════════════════════

function renderMisPartyRows(rows = [], label) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<tr><td colspan="4" class="muted">No ${escapeHtml(label)} outstanding in the open-item aging contract.</td></tr>`;
  }
  return rows.slice(0, 5).map((row) => `
    <tr>
      <td>${escapeHtml(row.rank || "")}</td>
      <td>${escapeHtml(row.party_name || row.party_id || "Unallocated")}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.outstanding || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.overdue || 0))}</td>
    </tr>
  `).join("");
}

function renderMisKpiContractPanel(data) {
  if (!data) {
    return `<p class="muted">Loading source-backed MIS KPI contracts...</p>`;
  }

  const workingCapital = data.working_capital || {};
  const overdue = data.overdue || {};
  const receivables = overdue.receivables || {};
  const payables = overdue.payables || {};
  const trend = Array.isArray(data.monthly_sales_purchase_trend) ? data.monthly_sales_purchase_trend : [];
  const trendRows = trend.length ? trend.slice(-6).map((row) => `
    <tr>
      <td>${escapeHtml(row.month || "")}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.sales || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.purchases || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.net || 0))}</td>
    </tr>
  `).join("") : `<tr><td colspan="4" class="muted">No monthly posted sales or purchase trend yet.</td></tr>`;

  return `
    <div class="preview-heading compact">
      <div>
        <p>${escapeHtml(data.financial_health?.summary || "Monthly trends, top parties, working capital, and overdue dashboards are source-backed.")}</p>
      </div>
      <span class="pill ok">as of ${escapeHtml(data.as_of || todayIsoDate())}</span>
    </div>
    <div class="metric-grid four">
      ${renderStatCards([
        ["Working capital", formatCurrency(workingCapital.net_working_capital || 0), `current ratio ${workingCapital.current_ratio ?? "--"}x`],
        ["Receivables overdue", formatCurrency(receivables.overdue || 0), `${formatCurrency(receivables.over_90 || 0)} over 90 days`],
        ["Payables overdue", formatCurrency(payables.overdue || 0), `${formatCurrency(payables.over_90 || 0)} over 90 days`],
        ["Source", "Posted ledger", "open-item aging"],
      ])}
    </div>
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Monthly Sales / Purchase Trend</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>Month</th><th>Sales</th><th>Purchases</th><th>Net</th></tr></thead>
            <tbody>${trendRows}</tbody>
          </table>
        </div>
      </article>
      <article>
        <h4>Top Customers</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>#</th><th>Customer</th><th>Outstanding</th><th>Overdue</th></tr></thead>
            <tbody>${renderMisPartyRows(data.top_customers, "customer")}</tbody>
          </table>
        </div>
      </article>
      <article>
        <h4>Top Vendors</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>#</th><th>Vendor</th><th>Outstanding</th><th>Overdue</th></tr></thead>
            <tbody>${renderMisPartyRows(data.top_vendors, "vendor")}</tbody>
          </table>
        </div>
      </article>
    </div>
  `;
}

function renderBusinessExecutiveDashboard() {
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const partyCount = Array.isArray(lastBusinessParties) ? lastBusinessParties.length : 0;
  const accountCount = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;

  // Live dashboard data from GET /business/dashboard (computed from the ledger).
  // No hard-coded fallbacks: before data loads or with an empty ledger we show
  // real zeros rather than invented figures.
  const dashboardData = lastBusinessDashboardStats || {};
  const hasDashboard = !!lastBusinessDashboardStats;

  // Lazy self-heal: whenever the KPI dashboard renders without data (boot,
  // refresh, or any path that didn't fetch), kick off the load. Deferred so we
  // don't re-enter during the current innerHTML render; guarded so it fires once.
  if (hasTrustedSession() && !hasDashboard && !businessDashboardLoadInFlight) {
    setTimeout(() => { loadBusinessDashboardStats(); }, 0);
  }
  if (hasTrustedSession() && !lastBusinessMisKpis && !businessMisLoadInFlight) {
    setTimeout(() => { loadBusinessMisKpis(); }, 0);
  }

  // KPI values (Rupees). FYTD = financial-year-to-date.
  const incomeVal = Number(dashboardData.income?.fytd || 0);
  const expenseVal = Number(dashboardData.expenses?.fytd || 0);
  const netVal = Number(dashboardData.net_position?.profit_loss || 0);
  const incomeGrowth = Number(dashboardData.income?.ytd_growth || 0);
  const cashVal = Number(dashboardData.cash_and_bank || 0);
  const receivablesVal = Number(dashboardData.receivables || 0);
  const payablesVal = Number(dashboardData.payables || 0);
  const gstStatus = dashboardData.gst?.status || "—";

  const incomeDisplay = formatCurrency(incomeVal);
  const expenseDisplay = formatCurrency(expenseVal);
  const netDisplay = formatCurrency(netVal);

  // 6-month income-vs-expense trend (lakhs) from the ledger; empty when no activity.
  const months = Array.isArray(dashboardData.monthly_trend) ? dashboardData.monthly_trend : [];
  const trendValues = months.flatMap(([, income, expense]) => [Number(income) || 0, Number(expense) || 0]);
  const maxValue = trendValues.length ? Math.max(...trendValues, 0.0001) : 1;
  const bars = months.length
    ? months.map(([label, income, expense]) => {
        const inc = Number(income) || 0;
        const exp = Number(expense) || 0;
        const incomeHeight = Math.max(4, Math.round((inc / maxValue) * 132));
        const expenseHeight = Math.max(4, Math.round((exp / maxValue) * 132));
        return `
      <div class="finance-bar-group">
        <div class="finance-bars" aria-label="${escapeHtml(label)} income Rs. ${inc}L and expenses Rs. ${exp}L">
          <span class="income-bar" style="height: ${incomeHeight}px"></span>
          <span class="expense-bar" style="height: ${expenseHeight}px"></span>
        </div>
        <small>${escapeHtml(label)}</small>
      </div>
    `;
      }).join("")
    : `<p class="muted">${hasDashboard ? "No ledger activity in the last 6 months." : "Loading ledger activity…"}</p>`;

  // Widget 1: KPI Strip (Phase 2C.2-C.3: Collapsible & Customizable)
  const kpiStripContent = `
    <div class="executive-hero kpi-widget-hero">
      <div class="executive-kpi-strip">
        <article>
          <span>Income</span>
          <strong>${escapeHtml(incomeDisplay)}</strong>
          <small>${incomeGrowth > 0 ? "+" : ""}${incomeGrowth.toFixed(1)}% vs last month</small>
        </article>
        <article>
          <span>Expenses</span>
          <strong>${escapeHtml(expenseDisplay)}</strong>
          <small>Office, purchases, vendor bills</small>
        </article>
        <article>
          <span>Net Position</span>
          <strong>${escapeHtml(netDisplay)}</strong>
          <small>Income − Expenses (FYTD)</small>
        </article>
      </div>
    </div>
  `;

  // Widget 2: Finance Chart (Phase 2C.2-C.3: Collapsible & Customizable)
  const financeChartContent = `
    <div class="preview-heading compact">
      <div>
        <p>Scoped performance metrics for the active BUSINESS Suite.</p>
      </div>
      <span class="pill ok">CEO view</span>
    </div>
    <div class="finance-chart" role="img" aria-label="Monthly income and expense bar chart">
      ${bars}
    </div>
    <div class="chart-legend">
      <span><i class="income-dot"></i>Income</span>
      <span><i class="expense-dot"></i>Expenses</span>
    </div>
  `;

  // Widget 3: CEO Panel — real metrics derived from the live ledger figures above.
  const coverage = payablesVal > 0 ? cashVal / payablesVal : null;
  const coverageRow = coverage != null
    ? `<strong>${coverage.toFixed(1)}x coverage</strong><span>Cash & bank (${formatCurrency(cashVal)}) against vendor dues (${formatCurrency(payablesVal)}).</span>`
    : `<strong>${escapeHtml(formatCurrency(cashVal))}</strong><span>Cash & bank on hand. No outstanding vendor dues.</span>`;
  const ceoPanelContent = `
    <div class="preview-heading compact">
      <div class="ceo-title-block">
        <span class="ceo-orbit" aria-hidden="true"></span>
        <span class="ai-badge">Live from ledger</span>
        <p>Key operating figures computed from posted entries (as of ${escapeHtml(dashboardData.as_of || todayIsoDate())}).</p>
      </div>
    </div>
    <div class="ceo-insight-list" role="list">
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">${coverageRow}</div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(receivablesVal))}</strong>
          <span>Outstanding from customers (open receivables).</span>
        </div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(netVal))}</strong>
          <span>Net position this financial year (income − expenses).</span>
        </div>
      </div>
    </div>
    <p class="ceo-footnote">${voucherCount} posted voucher(s), ${partyCount} party record(s), and ${accountCount} account(s) in this dashboard context. GST: ${escapeHtml(gstStatus)}.</p>
  `;

  // Build dashboard with wrapped widgets (Phase 2C.2-C.3)
  const kpiWidget = createWidgetWrapper("kpi-strip", "Key Performance Indicators", kpiStripContent, true);
  const chartWidget = createWidgetWrapper("finance-chart", "Sales & Expenses Trend", financeChartContent, true);
  const ceoWidget = createWidgetWrapper("ceo-panel", "CEO Insights", ceoPanelContent, true);
  const misWidget = createWidgetWrapper("mis-kpi-contracts", "MIS KPI Contracts", renderMisKpiContractPanel(lastBusinessMisKpis), true);

  return `
    <section class="executive-dashboard" aria-label="MitraBooks executive dashboard">
      <div class="dashboard-toolbar">
        <button
          class="dashboard-customize-btn"
          type="button"
          data-business-action="open-widget-settings"
          aria-label="Customize dashboard widgets"
          title="Customize widgets"
        >⚙ Customize</button>
      </div>
      ${kpiWidget}
      <div class="finance-dashboard-grid-wrapper">
        ${chartWidget}
        ${ceoWidget}
      </div>
      ${misWidget}
    </section>
  `;
}

function resultPayload(result, fallback) {
  return result && result.ok ? result.payload : fallback;
}

function resultRows(result) {
  const payload = resultPayload(result, []);
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.rows)) {
    return payload.rows;
  }
  return [];
}

function statusDetailText(payload) {
  if (!payload) {
    return "";
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (Array.isArray(payload)) {
    return payload.map(statusDetailText).filter(Boolean).join("; ");
  }
  if (typeof payload === "object") {
    const direct = payload.detail || payload.message || payload.error;
    if (direct) {
      return statusDetailText(direct);
    }
    const textValues = Object.values(payload)
      .map((value) => statusDetailText(value))
      .filter(Boolean);
    return textValues.slice(0, 3).join("; ");
  }
  return String(payload);
}

function renderStatusBlock(title, result) {
  if (!result || result.ok) {
    return "";
  }
  const detail = statusDetailText(result.payload);
  return `<div class="module-state warn"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail || "Unable to load this GruhaMitra compatibility endpoint.")}</span></div>`;
}

function currentBillingPeriodQuery() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const year = now.getFullYear();
  return `month=${encodeURIComponent(month)}&year=${encodeURIComponent(year)}`;
}

function renderSimpleTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.slice(0, 12).map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function mandirWorkspaceFromModule(module = {}) {
  const path = String(module.frontend_path || "").toLowerCase();
  const displayName = String(module.display_name || "").toLowerCase();
  if (path.includes("/donations") || displayName.includes("donation")) {
    return "donations";
  }
  if (path.includes("/devotees") || displayName.includes("devotee")) {
    return "devotees";
  }
  if (path.includes("/sevas") || displayName.includes("seva")) {
    return "sevas";
  }
  if (path.includes("/public-payments") || displayName.includes("public payment")) {
    return "payments";
  }
  if (path.includes("/receipts") || displayName.includes("receipt")) {
    return "receipts";
  }
  if (path.includes("/panchang") || displayName.includes("panchang")) {
    return "panchang";
  }
  if (path.includes("/reports") || displayName.includes("report")) {
    return "reports";
  }
  if (path.includes("/settings") || displayName.includes("setting")) {
    return "settings";
  }
  if (path.includes("/implementation") || displayName.includes("implementation")) {
    return "implementation";
  }
  if (path.includes("/platform-owner") || displayName.includes("platform owner")) {
    return "platform-owners";
  }
  if (path.includes("/accounting") || displayName.includes("accounting")) {
    return "accounting";
  }
  if (path.includes("/dashboard") || displayName.includes("dashboard")) {
    return "overview";
  }
  return "";
}

function platformWorkspaceFromModule(module = {}) {
  const path = String(module.frontend_path || "").toLowerCase();
  const displayName = String(module.display_name || "").toLowerCase();
  if (path.includes("/onboarding") || displayName.includes("onboarding")) {
    return "onboarding";
  }
  if (path.includes("/tenants") || displayName.includes("tenant")) {
    return "tenants";
  }
  if (path.includes("/subscriptions") || displayName.includes("subscription")) {
    return "subscriptions";
  }
  return "dashboard";
}

function navIconForMandirWorkspace(workspace) {
  return ({
    overview: "▦",
    sevas: "♜",
    "book-sevas": "♜",
    "seva-bookings": "▤",
    "seva-management": "▤",
    "reschedule-approval": "✓",
    donations: "▰",
    devotees: "●●",
    payments: "▣",
    receipts: "▤",
    reports: "▥",
    panchang: "□",
    settings: "⚙",
    implementation: "☑",
    "platform-owners": "♜",
    accounting: "▣",
  }[workspace] || "");
}

function syncMandirNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.mandirWorkspace || "";
    const isActive = currentExperience === "mandir" && workspace && workspace === activeMandirWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent) {
    const labels = {
      overview: "Dashboard",
      donations: "Donations",
      sevas: "Sevas",
      payments: "Public Payments",
      exceptions: "Exceptions",
      receipts: "Receipts",
      panchang: "Panchang",
      reports: "Reports",
      accounting: "Accounting",
      settings: "Settings",
      implementation: "Implementation Checks",
      "platform-owners": "Platform Owners",
    };
    const gruhaLabels = {
      overview: "Dashboard",
      maintenance: "Maintenance",
      members: "Members",
      flats: "Flats",
      complaints: "Complaints",
      messages: "Messages",
      meetings: "Meetings",
      assets: "Assets",
      accounting: "Accounting",
      reports: "Reports",
      settings: "Settings",
    };
    topbarCurrent.textContent = currentExperience === "mandir"
      ? labels[activeMandirWorkspace] || "Dashboard"
      : currentExperience === "gruha"
        ? gruhaLabels[activeGruhaWorkspace] || "Dashboard"
        : "Dashboard";
  }
}

function syncGruhaNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.gruhaWorkspace || "";
    const isActive = currentExperience === "gruha" && workspace && workspace === activeGruhaWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "gruha") {
    const labels = {
      overview: "Dashboard",
      maintenance: "Maintenance",
      members: "Members",
      flats: "Flats",
      complaints: "Complaints",
      messages: "Messages",
      meetings: "Meetings",
      assets: "Assets",
      accounting: "Accounting",
      reports: "Reports",
      settings: "Settings",
    };
    topbarCurrent.textContent = labels[activeGruhaWorkspace] || "Dashboard";
  }
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: SHARED UTILITIES
// NOTE  : escapeHtml, formatCurrency, formatCountLabel, setLoginStatus, statusDetailText, delay
// ══════════════════════════════════════════════════════════════════════

function syncPlatformNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.platformWorkspace || "";
    const isActive = currentExperience === "platform" && workspace && workspace === activePlatformWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "platform") {
    const labels = {
      dashboard: "Dashboard",
      onboarding: "Onboarding Requests",
      tenants: "Tenant Status",
      subscriptions: "Subscriptions",
    };
    const label = labels[activePlatformWorkspace] || "Dashboard";
    topbarCurrent.textContent = label;
    updatePageHeader("Platform Owner", label, `${label} Workspace`);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function formatCountMap(value) {
  if (!value || typeof value !== "object") {
    return "none";
  }
  return Object.entries(value)
    .map(([key, count]) => `${escapeHtml(key)}: ${escapeHtml(count)}`)
    .join(", ") || "none";
}

function renderPlatformTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${emptyText}</p>`;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderPendingApprovalsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No pending onboarding approvals.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Request</th>
            <th>App</th>
            <th>Organization</th>
            <th>Admin Email</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const requestId = row.request_id || row.id || "";
            return `
              <tr>
                <td>${escapeHtml(requestId)}</td>
                <td>${escapeHtml(row.app_key)}</td>
                <td>${escapeHtml(row.organization_name || row.tenant_name)}</td>
                <td>${escapeHtml(row.admin_email)}</td>
                <td>
                  <div class="action-row">
                    <button type="button" data-platform-action="approve" data-request-id="${escapeHtml(requestId)}">Approve</button>
                    <button class="secondary" type="button" data-platform-action="reject" data-request-id="${escapeHtml(requestId)}">Reject</button>
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function mandirPublicPaymentPageUrl() {
  const api = encodeURIComponent(getConfiguredApiBaseUrl());
  return `../mandir-public/?api=${api}`;
}

function renderMandirOperationResult(result) {
  if (!result) {
    return "";
  }
  return `
    <div class="module-state ${result.ok ? "ok" : "warn"}" id="mandir-operation-result">
      <strong>${escapeHtml(result.title || (result.ok ? "Operation completed" : "Operation failed"))}</strong>
      <span>${escapeHtml(result.detail || "")}</span>
    </div>
  `;
}

function setLoginStatus(kind, title, detail = "") {
  if (!loginStatus) {
    return;
  }
  loginStatus.className = `module-state ${kind || ""}`.trim();
  loginStatus.innerHTML = title
    ? `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span>`
    : "";
}

function isPasswordRecoveryPanelOpen() {
  const forgotOpen = Boolean(forgotPasswordForm && !forgotPasswordForm.hasAttribute("hidden"));
  const resetOpen = Boolean(resetPasswordForm && !resetPasswordForm.hasAttribute("hidden"));
  return forgotOpen || resetOpen;
}

function setAuthPanelMode(mode) {
  const normalized = mode === "forgot" || mode === "reset" ? mode : "login";
  const title = document.getElementById("access-title");
  const copy = document.getElementById("access-copy");
  const loginForm = document.getElementById("login-form");
  loginForm?.toggleAttribute("hidden", normalized !== "login");
  forgotPasswordForm?.toggleAttribute("hidden", normalized !== "forgot");
  resetPasswordForm?.toggleAttribute("hidden", normalized !== "reset");
  if (title) {
    title.textContent = normalized === "forgot"
      ? "Reset password"
      : normalized === "reset"
        ? "Set new password"
        : "Sign in";
  }
  if (copy) {
    copy.textContent = normalized === "forgot"
      ? "Enter your MitraBooks account email. If it exists, a reset link will be sent."
      : normalized === "reset"
        ? "Choose a new password for your MitraBooks account."
        : "Use your tenant admin credentials to open the workspace.";
  }
}

function showAuthFieldMessage(fieldId, message) {
  const field = document.getElementById(fieldId);
  const messageNode = field?.querySelector("p");
  if (field) field.hidden = false;
  if (messageNode) messageNode.textContent = message;
}

function clearAuthFieldMessage(fieldId) {
  const field = document.getElementById(fieldId);
  const messageNode = field?.querySelector("p");
  if (field) field.hidden = true;
  if (messageNode) messageNode.textContent = "";
}

async function requestPasswordReset() {
  const email = String(forgotPasswordEmail?.value || loginEmail?.value || "").trim().toLowerCase();
  const submitButton = document.getElementById("forgot-password-submit");
  clearAuthFieldMessage("forgot-error-field");
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showAuthFieldMessage("forgot-error-field", "Enter a valid account email.");
    setLoginStatus("warn", "Email required", "Enter the MitraBooks account email to request a reset link.");
    return;
  }
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Sending...";
  }
  const result = await apiRequest(APP_KEY, "/api/v1/auth/forgot-password", {
    method: "POST",
    timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
    body: JSON.stringify({ email }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Send reset link";
  }
  if (result.ok) {
    window.localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email);
    if (loginEmail) loginEmail.value = email;
    setLoginStatus("ok", "Reset link requested", result.payload?.message || "If this account exists, password reset instructions have been sent.");
  } else {
    const detail = statusDetailText(result.payload?.detail) || "Password reset email could not be sent. Please try again.";
    showAuthFieldMessage("forgot-error-field", detail);
    setLoginStatus("danger", "Reset request failed", detail);
  }
  renderJson(apiOutput, { forgot_password: { ok: result.ok, status: result.status } });
}

async function completePasswordReset() {
  const newPassword = String(resetNewPasswordInput?.value || "");
  const confirmPassword = String(resetConfirmPasswordInput?.value || "");
  const submitButton = document.getElementById("reset-password-submit");
  clearAuthFieldMessage("reset-error-field");
  if (!pendingPasswordResetToken) {
    showAuthFieldMessage("reset-error-field", "Reset token is missing or expired. Request a new reset link.");
    return;
  }
  if (newPassword.length < 6) {
    showAuthFieldMessage("reset-error-field", "Password must be at least 6 characters.");
    return;
  }
  if (newPassword !== confirmPassword) {
    showAuthFieldMessage("reset-error-field", "Password and confirm password do not match.");
    return;
  }
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Updating...";
  }
  const result = await apiRequest(APP_KEY, "/api/v1/auth/reset-password", {
    method: "POST",
    timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
    body: JSON.stringify({
      token: pendingPasswordResetToken,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Update password";
  }
  if (result.ok) {
    pendingPasswordResetToken = "";
    resetPasswordForm?.reset();
    if (window.history?.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    setAuthPanelMode("login");
    setLoginStatus("ok", "Password updated", "Use the new password to sign in.");
  } else {
    const detail = statusDetailText(result.payload?.detail) || "Password could not be updated. Request a new reset link.";
    showAuthFieldMessage("reset-error-field", detail);
    setLoginStatus("danger", "Password reset failed", detail);
  }
  renderJson(apiOutput, { reset_password: { ok: result.ok, status: result.status } });
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function showMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  const splashConfig = currentExperience === "mandir"
    ? {
        video: "../assets/brand/mandirmitra-logo.mp4",
        image: "../assets/brand/mandirmitra-logo.jpeg",
        alt: "MandirMitra",
        copy: "Opening MandirMitra dashboard...",
      }
    : {
        video: "../assets/brand/mitrabooks-pro-logo.mp4",
        image: "../assets/brand/mitrabooks-pro-logo.png",
        alt: "MitraBooks",
        copy: "Opening MitraBooks dashboard...",
      };
  if (mandirSplashVideo) {
    mandirSplashVideo.src = splashConfig.video;
  }
  if (mandirSplashImage) {
    mandirSplashImage.src = splashConfig.image;
    mandirSplashImage.alt = splashConfig.alt;
  }
  if (brandSplashCopy) {
    brandSplashCopy.textContent = splashConfig.copy;
  }
  mandirSplash.classList.add("show");
  mandirSplash.setAttribute("aria-hidden", "false");
  if (mandirSplashVideo) {
    mandirSplashVideo.currentTime = 0;
    await mandirSplashVideo.play().catch(() => {});
  }
}

function hideMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  mandirSplash.classList.remove("show");
  mandirSplash.setAttribute("aria-hidden", "true");
  mandirSplashVideo?.pause();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: AUTH + SESSION
// API   : POST /api/v1/auth/login  POST /api/v1/auth/change-password
// NOTE  : signInWithPassword, signOutAndReturnToLogin, hasTrustedSession, updateSessionUi
// ══════════════════════════════════════════════════════════════════════

let pendingForcedPasswordChange = false;

function hasTrustedSession() {
  if (!getAccessToken()) {
    return false;
  }
  if (currentExperience !== "mitrabooks") {
    return true;
  }
  return Boolean(lastModuleContext && typeof lastModuleContext === "object");
}

function updateSessionUi() {
  const signedIn = hasTrustedSession();
  appRoot.classList.toggle("signed-in", signedIn);
  appRoot.classList.toggle("signed-out", !signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-in", signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-out", !signedIn);
  if (sessionPill) {
    sessionPill.textContent = signedIn ? "Signed in" : "Not signed in";
    sessionPill.className = `pill ${signedIn ? "ok" : "warn"}`;
  }
  const savedEmail = window.localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY) || "";
  if (topbarUser) {
    topbarUser.textContent = compactAccountLabel(savedEmail || "Signed in");
    topbarUser.title = savedEmail || "Signed in";
  }
  if (topbarAvatar) {
    topbarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarAvatar) {
    sidebarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarUserName) {
    sidebarUserName.textContent = signedIn ? (savedEmail || "Signed in") : "Not signed in";
  }
  if (sidebarUserRole) {
    const role = lastModuleContext?.role || lastModuleContext?.user_role || "";
    sidebarUserRole.textContent = signedIn ? (role || "Tenant context pending") : "Sign in to load tenant";
  }

  // Update user credentials display in topbar
  const emailDisplay = document.getElementById("topbar-email-display");
  const menuEmailDisplay = document.getElementById("menu-email-display");
  const menuTenantDisplay = document.getElementById("menu-tenant-display");
  if (emailDisplay) {
    emailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuEmailDisplay) {
    menuEmailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuTenantDisplay && lastModuleContext?.tenant_id) {
    menuTenantDisplay.textContent = lastModuleContext.tenant_id;
  }

  document.getElementById("topbar-actions")?.toggleAttribute("hidden", !signedIn);
  document.getElementById("sidebar-logout")?.toggleAttribute("hidden", !signedIn);
  if (loginEmail && !loginEmail.value) {
    loginEmail.value = savedEmail || DEFAULT_MITRABOOKS_LOGIN_EMAIL;
  }
  if (tokenInput) {
    tokenInput.value = getAccessToken();
  }
  const publicLink = document.getElementById("mandir-public-link");
  if (publicLink) {
    publicLink.href = mandirPublicPaymentPageUrl();
  }
}

function compactAccountLabel(email) {
  const value = String(email || "").trim();
  if (!value.includes("@")) {
    return value || "Account";
  }
  const [name, domain] = value.split("@");
  const shortName = name.length > 12 ? `${name.slice(0, 10)}...` : name;
  const shortDomain = String(domain || "").split(".")[0] || domain;
  return `${shortName}@${shortDomain}`;
}

function signOutAndReturnToLogin() {
  const rt = getRefreshToken();
  if (rt) {
    const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
    apiRequest(appKey, "/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: rt }),
    }).catch(() => {});
  }
  clearAllTokens();
  lastModuleContext = null;
  lastBusinessAccounts = [];
  lastBusinessParties = [];
  lastBusinessVouchers = [];
  lastVoucherApprovalQueue = [];
  lastAccountingDrilldown = null;
  if (tokenInput) {
    tokenInput.value = "";
  }
  if (loginPassword) {
    loginPassword.value = "";
  }
  setAuthPanelMode("login");
  setLoginStatus("", "", "");
  dashboardPreview.innerHTML = "";
  renderJson(apiOutput, {});
  renderModuleState(moduleState);
  currentExperience = initialExperience();
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${currentExperience}`)?.classList.add("active");
  renderModules();
  updateSessionUi();
}

function closeAccountMenu() {
  if (accountMenuPanel) {
    accountMenuPanel.hidden = true;
  }
  accountMenuTrigger?.setAttribute("aria-expanded", "false");
}

function openPasswordDialog() {
  closeAccountMenu();
  passwordForm?.reset();
  _clearPasswordError();
  if (passwordStatus && pendingForcedPasswordChange) {
    const field = document.getElementById("password-error-field");
    if (field) field.style.display = "block";
    passwordStatus.className = "module-state warn";
    passwordStatus.innerHTML = "<strong>Temporary password in use</strong><span>Change the temporary password before opening the MitraBooks workspace.</span>";
  }
  passwordDialog?.showModal();
}

async function loadCurrentUserProfile(appKey) {
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const result = await apiRequest(appKey, "/api/v1/users/me", {
    method: "GET",
    timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return result.ok ? (result.payload || null) : null;
}

async function completeWorkspaceSignIn(appKey) {
  if (currentExperience === "mitrabooks") {
    loadAndRenderGroupedNav(appKey).catch(err => {
      console.error("[Login] Failed to load grouped nav:", err);
    });
  }

  await showMandirSplash();
  try {
    const checks = runChecks();
    const loadingBudget = delay(8000).then(() => ({ timedOut: true }));
    const result = await Promise.race([
      checks.then(() => ({ timedOut: false })),
      loadingBudget,
    ]);
    await delay(700);
    if (result.timedOut) {
      checks.catch((error) => {
        console.error("[Login] Background workspace load failed:", error);
      });
      setLoginStatus("warn", "Workspace is still loading", "Dashboard checks are continuing in the background.");
    }
  } finally {
    hideMandirSplash();
  }
}

function _showPasswordError(msg) {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "block";
  if (passwordStatus) {
    passwordStatus.className = "module-state danger";
    passwordStatus.innerHTML = msg;
  }
}

function _clearPasswordError() {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "none";
  if (passwordStatus) {
    passwordStatus.className = "module-state";
    passwordStatus.textContent = "";
  }
}

async function updateCurrentPassword() {
  const currentPassword = String(currentPasswordInput?.value || "");
  const newPassword = String(newPasswordInput?.value || "");
  const confirmPassword = String(confirmNewPasswordInput?.value || "");
  const submitButton = document.getElementById("change-password-submit");

  if (!currentPassword || currentPassword.length < 6) {
    _showPasswordError("<strong>Current password required</strong><span>Enter the current account password first.</span>");
    return;
  }
  if (!newPassword || newPassword.length < 6) {
    _showPasswordError("<strong>New password too short</strong><span>Use at least 6 characters.</span>");
    return;
  }
  if (newPassword !== confirmPassword) {
    _showPasswordError("<strong>Passwords do not match</strong><span>Confirm the new password again.</span>");
    return;
  }
  _clearPasswordError();

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Updating...";
  }
  const result = await apiRequest(APP_KEY, "/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Update Password";
  }

  if (result.ok) {
    const wasForcedPasswordChange = pendingForcedPasswordChange;
    pendingForcedPasswordChange = false;
    passwordForm?.reset();
    if (passwordStatus) {
      passwordStatus.className = "module-state ok";
      passwordStatus.innerHTML = "<strong>Password updated</strong><span>Use the new password for your next sign-in.</span>";
    }
    passwordDialog?.close();
    if (wasForcedPasswordChange) {
      setLoginStatus("ok", "Password updated", "Password changed. Loading your MitraBooks workspace.");
      await completeWorkspaceSignIn(EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY);
    } else {
      setLoginStatus("ok", "Password updated", "Use the new password for your next sign-in.");
    }
  } else {
    _showPasswordError(`<strong>Password update failed</strong><span>${escapeHtml(statusDetailText(result.payload?.detail) || statusDetailText(result.payload) || "Try again.")}</span>`);
  }
  renderJson(apiOutput, { change_password: { ok: result.ok, status: result.status, detail: result.payload?.detail } });
}

function activeOrgSelectorType(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  return selectedOrgType || organizationType || "BUSINESS";
}

function syncOrgSelectorOptions(orgType) {
  document.querySelectorAll(".org-option").forEach((option) => {
    option.classList.toggle("active", option.getAttribute("data-org") === orgType);
  });
}

function updateTrustedContextUi(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  const selectorOrgType = activeOrgSelectorType(context);
  const selectorMeta = orgSelectorMeta[selectorOrgType] || orgSelectorMeta.BUSINESS;
  const tenantLabel = context?.tenant_name || context?.organization_name || context?.tenant_id || "";
  const enabledCount = Array.isArray(context?.enabled_modules)
    ? context.enabled_modules.length
    : Array.isArray(context?.modules)
      ? context.modules.filter((module) => module.enabled !== false).length
      : 0;

  if (currentOrgType) {
    currentOrgType.textContent = selectorMeta.label;
  }
  if (currentOrgTenant) {
    currentOrgTenant.textContent = selectorOrgType === "BUSINESS"
      ? tenantLabel || selectorMeta.subtitle
      : selectorMeta.subtitle;
  }
  syncOrgSelectorOptions(selectorOrgType);
  if (sidebarUserRole && getAccessToken()) {
    const role = context?.role || context?.user_role || "";
    sidebarUserRole.textContent = role || (enabledCount ? `${enabledCount} enabled module(s)` : "Tenant context loaded");
  }
}

async function signInWithPassword() {
  const email = String(loginEmail?.value || "").trim().toLowerCase();
  const password = String(loginPassword?.value || "");
  const loginSubmitBtn = document.getElementById("login-submit");
  const errorField = document.getElementById("login-error-field");
  const errorMessage = document.getElementById("login-error-message");

  // Validate input
  if (!email || !password) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Email and password are required.";
    }
    setLoginStatus("warn", "Email and password required", "Enter your MitraBooks tenant admin login.");
    return;
  }

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Please enter a valid email address.";
    }
    setLoginStatus("warn", "Invalid email", "Email must be a valid email address.");
    return;
  }

  // Clear previous errors
  if (errorField) {
    errorField.hidden = true;
  }

  // Disable button and show loading state
  if (loginSubmitBtn) {
    loginSubmitBtn.disabled = true;
    loginSubmitBtn.textContent = "Signing in...";
  }

  try {
    setLoginStatus("", "Signing in", "Checking your tenant access...");
    const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
    const result = await apiRequest(appKey, "/api/v1/auth/login", {
      method: "POST",
      timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
      body: JSON.stringify({ email, password }),
    });

    if (!result.ok) {
      clearAccessToken();
      updateSessionUi();
      const detail = statusDetailText(result.payload?.detail) ||
        statusDetailText(result.payload) ||
        "Unable to sign in with these credentials.";

      // Show error message in form
      if (errorField && errorMessage) {
        errorField.hidden = false;
        errorMessage.textContent = detail;
      }

      setLoginStatus("danger", "Sign in failed", detail);
      renderJson(apiOutput, { login: { ok: result.ok, status: result.status, detail } });
      return;
    }

    // Successful login
    setAccessToken(result.payload?.access_token || "");
    setRefreshToken(result.payload?.refresh_token || "");
    window.localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email);

    // Clear password for security
    if (loginPassword) {
      loginPassword.value = "";
    }

    updateSessionUi();
    renderJson(apiOutput, { login: { ok: true, status: result.status, token_type: result.payload?.token_type || "bearer" } });
    const currentUser = await loadCurrentUserProfile(appKey);
    pendingForcedPasswordChange = Boolean(currentUser?.must_change_password);
    if (pendingForcedPasswordChange) {
      setLoginStatus("warn", "Temporary password in use", "Change the temporary password to continue into the MitraBooks workspace.");
      openPasswordDialog();
      return;
    }
    setLoginStatus("ok", "Signed in", "Tenant workspace is loading.");
    await completeWorkspaceSignIn(appKey);
  } catch (error) {
    console.error("[Login] Error during sign in:", error);
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "An unexpected error occurred. Please try again.";
    }
    setLoginStatus("danger", "Sign in error", "An unexpected error occurred. Please try again.");
  } finally {
    // Re-enable button
    if (loginSubmitBtn) {
      loginSubmitBtn.disabled = false;
      loginSubmitBtn.textContent = "Sign in";
    }
  }
}


// ══════════════════════════════════════════════════════════════════════

function renderRecentTenantsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No tenants returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Tenant</th>
            <th>Status</th>
            <th>Org Type</th>
            <th>Plan</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const tenantId = row.tenant_id || "";
            const modules = Array.isArray(row.enabled_modules) ? row.enabled_modules.join(",") : "";
            return `
              <tr>
                <td>${escapeHtml(row.display_name || tenantId)}</td>
                <td>${escapeHtml(row.status)}</td>
                <td>${escapeHtml(row.organization_type)}</td>
                <td>${escapeHtml(row.subscription_plan)}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-platform-action="entitlements"
                    data-tenant-id="${escapeHtml(tenantId)}"
                    data-tenant-label="${escapeHtml(row.display_name || tenantId)}"
                    data-tenant-status="${escapeHtml(row.status)}"
                    data-organization-type="${escapeHtml(row.organization_type)}"
                    data-subscription-plan="${escapeHtml(row.subscription_plan)}"
                    data-enabled-modules="${escapeHtml(modules)}"
                    data-hr-addon-available="${row.hr_addon_available ? "1" : "0"}"
                  >Entitlements</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — financial reports (TB / I&E / B&P / BS)
// API   : GET /api/v1/mandir/reports/...
// NOTE  : renderMandirTrialBalance, renderMandirIncomeExpenditureReport, renderMandirBalanceSheetReport
// ══════════════════════════════════════════════════════════════════════

function formatCurrency(value) {
  const amount = Number(value || 0);
  return `Rs. ${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatCountLabel(count, singular, plural = `${singular}s`) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : plural}`;
}

function renderPlatformRecentOnboardingTable(rows) {
  return renderPlatformTable(rows, [
    { label: "Request", value: (row) => row.request_id || row.id || "" },
    { label: "App", value: (row) => row.app_key || "" },
    { label: "Status", value: (row) => row.status || "" },
    { label: "Payment", value: (row) => row.payment_status || "" },
    { label: "Documents", value: (row) => row.document_verification_status || "" },
    { label: "Admin Email", value: (row) => row.admin_email || "" },
  ], "No onboarding requests returned.");
}

function renderPlatformSubscriptionsTable(rows) {
  return renderPlatformTable(rows, [
    { label: "Tenant / Payer", value: (row) => row.display_name || row.payer_email || row.tenant_id || "" },
    { label: "Product", value: (row) => row.app_key || (Array.isArray(row.app_keys) ? row.app_keys.join(", ") : "") },
    { label: "Plan", value: (row) => row.subscription_plan || "" },
    { label: "Status", value: (row) => row.subscription_status || row.status || "" },
    { label: "Modules / Cycle", value: (row) => Array.isArray(row.enabled_modules) ? row.enabled_modules.join(", ") : (row.billing_cycle || "") },
  ], "No subscription records returned.");
}

function emptyPlatformDashboardPayload() {
  return {
    summary: {
      onboarding: { by_status: { pending: 0, payment_pending: 0, payment_received: 0, under_review: 0, approved: 0, rejected: 0 } },
      tenants: { by_status: { active: 0, inactive: 0 } },
      subscriptions: { by_plan: {} },
    },
    app_status: [
      { app_key: "legalmitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "mandirmitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "gruhamitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "mitrabooks", onboarding: { pending: 0 }, tenant_count: 0 },
    ],
    module_status: [],
    pending_approvals: [],
    recent_onboarding: [],
    recent_tenants: [],
    subscription_records: [],
  };
}

function renderPlatformDashboard(payload) {
  const summary = payload?.summary || {};
  const onboarding = summary.onboarding || {};
  const tenants = summary.tenants || {};
  const subscriptions = summary.subscriptions || {};
  const pending = onboarding.by_status?.pending || 0;
  const active = tenants.by_status?.active || 0;
  const inactive = tenants.by_status?.inactive || 0;
  const planCount = Object.keys(subscriptions.by_plan || {}).length;
  const appStatus = Array.isArray(payload?.app_status) ? payload.app_status : [];
  const moduleStatus = Array.isArray(payload?.module_status) ? payload.module_status : [];
  const pendingApprovals = Array.isArray(payload?.pending_approvals) ? payload.pending_approvals : [];
  const recentOnboarding = Array.isArray(payload?.recent_onboarding_requests)
    ? payload.recent_onboarding_requests
    : (Array.isArray(payload?.recent_onboarding) ? payload.recent_onboarding : []);
  const recentTenants = Array.isArray(payload?.recent_tenants) ? payload.recent_tenants : [];
  const subscriptionRecords = Array.isArray(payload?.subscription_records) ? payload.subscription_records : recentTenants;
  const workspace = activePlatformWorkspace || "dashboard";

  if (workspace === "onboarding") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Onboarding Requests</h3>
            <p>Review product onboarding requests, payment status, and document verification state.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <article>
          <h4>Pending Review</h4>
          ${renderPendingApprovalsTable(pendingApprovals)}
        </article>
        <article>
          <h4>Recent Onboarding Requests</h4>
          ${renderPlatformRecentOnboardingTable(recentOnboarding)}
        </article>
      </div>
    `;
  }

  if (workspace === "tenants") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Tenant Status</h3>
            <p>Inspect active and inactive tenants across LegalMitra, MandirMitra, GruhaMitra, and MitraBooks.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <div class="metric-grid three">${renderStatCards([
          ["Active Tenants", active, "currently enabled"],
          ["Inactive Tenants", inactive, "needs review"],
          ["Tracked Apps", appStatus.length, "product contexts"],
        ])}</div>
        <article>
          <h4>Recent Tenants</h4>
          ${renderRecentTenantsTable(recentTenants)}
        </article>
      </div>
    `;
  }

  if (workspace === "subscriptions") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Subscriptions</h3>
            <p>Check plan, subscription status, and enabled modules for tenant accounts.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <div class="metric-grid two">${renderStatCards([
          ["Subscription Plans", planCount, formatCountMap(subscriptions.by_plan)],
          ["Subscription Records", subscriptionRecords.length, "tenants and paid billing records"],
        ])}</div>
        <article>
          <h4>Tenant Subscriptions</h4>
          ${renderPlatformSubscriptionsTable(subscriptionRecords)}
        </article>
      </div>
    `;
  }

  return `
    <div class="legacy-dashboard platform-dashboard">
      <div class="preview-heading">
        <div>
          <h3>Platform Owner Dashboard</h3>
          <p>Read-only cross-module status for onboarding, subscriptions, tenants, and enabled modules.</p>
        </div>
        <span class="pill ok">super admin</span>
      </div>
      <div class="metric-grid four">${renderStatCards([
        ["Pending Approvals", pending, "module-wise onboarding"],
        ["Active Tenants", active, "all tracked apps"],
        ["Inactive Tenants", inactive, "needs review"],
        ["Subscription Plans", planCount, formatCountMap(subscriptions.by_plan)],
      ])}</div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Pending Approvals</h4>
          ${renderPendingApprovalsTable(pendingApprovals)}
        </article>
        <article>
          <h4>App Status</h4>
          <ul class="status-list">
            ${appStatus.map((row) => `
              <li>
                <strong>${escapeHtml(row.app_key)}</strong>
                <span>${escapeHtml(row.onboarding?.pending || 0)} pending, ${escapeHtml(row.tenant_count || 0)} tenant(s)</span>
              </li>
            `).join("")}
          </ul>
        </article>
      </div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Recent Tenants</h4>
          ${renderRecentTenantsTable(recentTenants)}
        </article>
        <article>
          <h4>Enabled Modules</h4>
          <ul class="status-list">
            ${moduleStatus.map((row) => `
              <li>
                <strong>${escapeHtml(row.module_key)}</strong>
                <span>${escapeHtml(row.tenant_count || 0)} tenant(s)</span>
              </li>
            `).join("")}
          </ul>
        </article>
      </div>
    </div>
  `;
}

function accountingDrilldownTitle(level) {
  return {
    month: "Monthly Voucher Drill Down",
    week: "Weekly Voucher Drill Down",
    day: "Daily Voucher Drill Down",
    voucher: "Voucher Level",
  }[level] || "Accounting Drill Down";
}

function renderAccountingDrilldownRows(payload) {
  const rows = Array.isArray(payload?.items) ? payload.items : [];
  if (rows.length === 0) {
    return `<p class="muted">No posted vouchers returned for this period.</p>`;
  }
  const level = payload.level || accountingDrilldownState.level;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Period / Voucher</th>
            <th>Vouchers</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th>Last Voucher</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const period = row.month || row.week_start || row.day || row.reference || row.id || "";
            const lastVoucher = row.last_voucher || row;
            const nextLevel = level === "month" ? "week" : level === "week" ? "day" : level === "day" ? "voucher" : "";
            return `
              <tr>
                <td>${escapeHtml(row.label || period)}</td>
                <td>${escapeHtml(row.voucher_count || 1)}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_credit))}</td>
                <td>${escapeHtml(lastVoucher?.reference || lastVoucher?.idempotency_key || lastVoucher?.id || "")}</td>
                <td>
                  ${nextLevel ? `
                    <button
                      class="secondary"
                      type="button"
                      data-accounting-action="drill"
                      data-next-level="${escapeHtml(nextLevel)}"
                      data-month="${escapeHtml(row.month || accountingDrilldownState.month || "")}"
                      data-week-start="${escapeHtml(row.week_start || accountingDrilldownState.week_start || "")}"
                      data-day="${escapeHtml(row.day || accountingDrilldownState.day || "")}"
                    >Open</button>
                  ` : `
                    <button
                      class="secondary"
                      type="button"
                      data-accounting-action="voucher-detail"
                      data-journal-id="${escapeHtml(row.id || "")}"
                    >View</button>
                  `}
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAccountingVoucherDetail(detail = lastAccountingVoucherDetail) {
  if (!detail) {
    return "";
  }
  if (detail.ok === false) {
    return `<p class="muted">Voucher detail unavailable.</p>`;
  }
  const lines = Array.isArray(detail.lines) ? detail.lines : [];
  const reversedBy = Array.isArray(detail.reversed_by_journal_ids) ? detail.reversed_by_journal_ids : [];
  const isReversal = Boolean(detail.reversal_of_journal_id);
  const isReversed = reversedBy.length > 0;
  return `
    <div class="table-preview compact-table">
      <h4>Voucher ${escapeHtml(detail.reference || detail.id)}</h4>
      <p class="muted">${escapeHtml(detail.entry_date || "")} | ${escapeHtml(detail.description || "Posted journal voucher")}</p>
      <p class="muted">
        Journal #${escapeHtml(detail.id || "")}
        ${isReversal ? ` | Reversal of journal #${escapeHtml(detail.reversal_of_journal_id)}` : ""}
        ${isReversed ? ` | Reversed by journal #${escapeHtml(reversedBy.join(", #"))}` : ""}
        ${isReversal ? `<span class="pill warn">reversal</span>` : isReversed ? `<span class="pill warn">reversed</span>` : `<span class="pill ok">posted</span>`}
      </p>
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Type</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${lines.map((line) => `
            <tr>
              <td>${escapeHtml(`${line.account_code || ""} ${line.account_name || ""}`.trim())}</td>
              <td>${escapeHtml(line.account_type || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAccountingDrilldownPanel(payload = lastAccountingDrilldown) {
  const state = accountingDrilldownState;
  const summary = payload?.summary || {};
  return `
    <div class="verification-panel accounting-drilldown-panel">
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(accountingDrilldownTitle(payload?.level || state.level))}</h4>
          <p>Drill from month to week to day and then to the posted voucher reference.</p>
        </div>
        <span class="pill">${escapeHtml(summary.voucher_count || 0)} vouchers</span>
      </div>
      <div class="list-filter-panel" data-accounting-drilldown>
        <div class="list-filter-bar">
          <label class="field">
            <span>From</span>
            <input name="from_date" type="date" value="${escapeHtml(state.from_date)}">
          </label>
          <label class="field">
            <span>To</span>
            <input name="to_date" type="date" value="${escapeHtml(state.to_date)}">
          </label>
          <label class="field">
            <span>Level</span>
            <select name="level">
              ${["month", "week", "day", "voucher"].map((level) => `<option value="${level}" ${state.level === level ? "selected" : ""}>${level}</option>`).join("")}
            </select>
          </label>
          <div class="list-filter-actions">
            <button type="button" data-accounting-action="apply-drilldown">Apply</button>
            <button class="secondary" type="button" data-accounting-action="reset-drilldown">Reset</button>
          </div>
        </div>
      </div>
      ${payload?.ok === false ? `<p class="muted">Accounting drill-down unavailable. Provide an access token with accounting access and run checks.</p>` : renderAccountingDrilldownRows(payload)}
      ${renderAccountingVoucherDetail()}
    </div>
  `;
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — panchang + operational reports
// API   : GET /api/v1/mandir/panchang  GET /api/v1/mandir/reports/operational
// NOTE  : renderMandirPanchang, renderMandirOperationalReports, renderMandirDevoteesView
// ══════════════════════════════════════════════════════════════════════

function panchangTimeRange(value) {
  if (!value || typeof value !== "object") {
    return "--";
  }
  const start = value.start || value.start_time || "";
  const end = value.end || value.end_time || "";
  return start && end ? `${start} - ${end}` : start || end || "--";
}

function renderMandirPanchang(payload = lastMandirPanchang) {
  if (!payload) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Today Panchang</h4>
            <p class="muted">Run checks to load temple-location Panchang for the active tenant.</p>
          </div>
        </div>
      </div>
    `;
  }
  if (payload.ok === false) {
    const detail = payload.payload?.detail || payload.detail || "Panchang is unavailable for the active temple tenant.";
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Today Panchang</h4>
            <p class="muted">${escapeHtml(detail)}</p>
          </div>
        </div>
      </div>
    `;
  }

  const date = payload.date || {};
  const hinduDate = date.hindu || {};
  const gregorianDate = date.gregorian || {};
  const location = payload.location || {};
  const panchang = payload.panchang || {};
  const tithi = panchang.tithi || {};
  const nakshatra = panchang.nakshatra || {};
  const yoga = panchang.yoga || {};
  const karana = panchang.karana || {};
  const vara = panchang.vara || {};
  const sunMoon = payload.sun_moon || {};
  const kaala = payload.kaala || payload.inauspicious_times || {};
  const muhurat = payload.muhurat || payload.auspicious_times || {};
  const festivals = Array.isArray(payload.festivals) ? payload.festivals : [];
  const specialNotes = payload.special_notes || {};

  const limbCards = [
    ["Tithi", tithi.full_name || tithi.name || "--", tithi.end_time_formatted ? `ends ${tithi.end_time_formatted}` : ""],
    ["Nakshatra", nakshatra.name || "--", nakshatra.end_time_formatted ? `ends ${nakshatra.end_time_formatted}` : ""],
    ["Yoga", yoga.name || "--", yoga.end_time_formatted ? `ends ${yoga.end_time_formatted}` : ""],
    ["Karana", karana.current || karana.name || "--", karana.end_time_formatted ? `ends ${karana.end_time_formatted}` : ""],
  ];
  const timingRows = [
    ["Sunrise", sunMoon.sunrise || "--", "Sunset", sunMoon.sunset || "--"],
    ["Rahu Kaal", panchangTimeRange(kaala.rahu || kaala.rahu_kaal), "Yamaganda", panchangTimeRange(kaala.yamaganda)],
    ["Gulika", panchangTimeRange(kaala.gulika), "Abhijit", panchangTimeRange(muhurat.abhijit || muhurat.abhijit_muhurat)],
    ["Brahma Muhurat", panchangTimeRange(muhurat.brahma || muhurat.brahma_muhurat), "Amrita Kalam", panchangTimeRange(kaala.amrita || muhurat.amrita_kalam)],
  ];

  return `
    <div class="verification-panel" id="mandir-panchang-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Today Panchang</h4>
          <p>${escapeHtml(gregorianDate.formatted || gregorianDate.date || "")} | ${escapeHtml(location.city || "Temple location")}</p>
        </div>
        <span class="pill ok">${escapeHtml(vara.name || gregorianDate.day || "Today")}</span>
      </div>
      <div class="metric-grid four">${renderStatCards(limbCards)}</div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Timing</th>
              <th>Value</th>
              <th>Timing</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            ${timingRows.map(([leftLabel, leftValue, rightLabel, rightValue]) => `
              <tr>
                <td>${escapeHtml(leftLabel)}</td>
                <td>${escapeHtml(leftValue)}</td>
                <td>${escapeHtml(rightLabel)}</td>
                <td>${escapeHtml(rightValue)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="table-preview compact-table">
        <table>
          <tbody>
            <tr>
              <th>Samvatsara</th>
              <td>${escapeHtml(hinduDate.samvatsara_name || payload.samvatsara?.name || "--")}</td>
              <th>Paksha</th>
              <td>${escapeHtml(hinduDate.paksha || tithi.paksha || "--")}</td>
            </tr>
            <tr>
              <th>Lunar Month</th>
              <td>${escapeHtml(hinduDate.month || hinduDate.lunar_month_purnimanta || "--")}</td>
              <th>Festivals</th>
              <td>${escapeHtml(festivals.map((item) => item.name || item.title).filter(Boolean).join(", ") || "None")}</td>
            </tr>
            <tr>
              <th>Recommendation</th>
              <td colspan="3">${escapeHtml(specialNotes.summary || "No special note for today.")}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function reportPayload(value, fallback = {}) {
  if (!value) {
    return fallback;
  }
  if (value.ok === false) {
    return fallback;
  }
  return value;
}

function reportRows(value, key) {
  const payload = reportPayload(value);
  return Array.isArray(payload[key]) ? payload[key] : [];
}

function renderMandirOperationalReports(reports = lastMandirOperationalReports) {
  const donationCategory = reportPayload(reports.donation_category);
  const donationDetail = reportPayload(reports.donation_detail);
  const sevaDetail = reportPayload(reports.seva_detail);
  const sevaSchedule = reportPayload(reports.seva_schedule);
  const devotees = Array.isArray(reports.devotees) ? reports.devotees : [];
  const categoryRows = reportRows(donationCategory, "categories");
  const donationRows = reportRows(donationDetail, "donations");
  const sevaRows = reportRows(sevaDetail, "sevas");
  const scheduleRows = reportRows(sevaSchedule, "schedule");
  const totalDonation = donationDetail.total_amount ?? donationCategory.total_amount ?? 0;
  const totalSeva = sevaDetail.total_amount ?? 0;
  const report80g = reportPayload(reports.compliance_80g);
  const reportFcra = reportPayload(reports.compliance_fcra);
  const rows80g = Array.isArray(report80g.items) ? report80g.items : [];
  const rowsFcra = Array.isArray(reportFcra.items) ? reportFcra.items : [];
  const fundSubledger = reportPayload(reports.fund_subledger);
  const fundRows = Array.isArray(fundSubledger.items) ? fundSubledger.items : [];
  const fundWise = reportPayload(reports.fund_wise);
  const festivalWise = reportPayload(reports.festival_wise);
  const fundDonationRows = Array.isArray(fundWise.items) ? fundWise.items : [];
  const festivalDonationRows = Array.isArray(festivalWise.items) ? festivalWise.items : [];
  const inventorySummary = reportPayload(reports.inventory_summary);
  const inventoryRows = Array.isArray(reports.inventory_stock_balances) ? reports.inventory_stock_balances : [];
  const inventoryMovements = Array.isArray(reports.inventory_movements) ? reports.inventory_movements : [];
  const inventoryConsumptions = Array.isArray(reports.inventory_consumptions) ? reports.inventory_consumptions : [];
  const pendingInventoryApprovals = inventoryConsumptions.filter((row) => row.status === "pending_approval").length;

  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>MandirMitra Reports</h4>
          <p>Donation, seva, devotee, and schedule reports for the active temple tenant.</p>
        </div>
        <span class="pill">${escapeHtml(accountingDrilldownState.from_date)} to ${escapeHtml(accountingDrilldownState.to_date)}</span>
      </div>
      <div class="metric-grid four">${renderStatCards([
        ["Donation Total", formatCurrency(totalDonation), formatCountLabel(donationRows.length, "receipt")],
        ["Seva Total", formatCurrency(totalSeva), formatCountLabel(sevaRows.length, "booking")],
        ["Devotees", devotees.length, "recent records"],
        ["Schedule", scheduleRows.length, "upcoming sevas"],
      ])}</div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Donation Category Report</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Category</th><th class="amount">Amount</th><th>Count</th></tr>
              </thead>
              <tbody>
                ${categoryRows.length ? categoryRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(row.category || "Uncategorized")}</td>
                    <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    <td>${escapeHtml(row.count ?? row.transaction_count ?? 0)}</td>
                  </tr>
                `).join("") : `<tr><td colspan="3">No donation categories for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Detailed Donations</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Receipt</th><th>Devotee</th><th>Purpose</th><th class="amount">Amount</th></tr>
              </thead>
              <tbody>
                ${donationRows.length ? donationRows.slice(0, 8).map((row) => {
                  const itemParts = [row.in_kind_item_name, row.in_kind_quantity].filter(Boolean).join(" / ");
                  const purposeDetail = row.donation_type === "in_kind" ? itemParts || "In-kind" : row.payment_mode || "Cash";
                  return `
                    <tr>
                      <td>${escapeHtml(String(row.date || row.receipt_date || "").slice(0, 10))}</td>
                      <td>${escapeHtml(row.receipt_number || row.id || "")}</td>
                      <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                      <td>
                        <strong>${escapeHtml(row.category || "Donation")}</strong>
                        <small>${escapeHtml(purposeDetail)}</small>
                      </td>
                      <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    </tr>
                  `;
                }).join("") : `<tr><td colspan="5">No donation receipts for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Detailed Sevas</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Seva</th><th>Devotee</th><th class="amount">Amount</th><th>Status</th></tr>
              </thead>
              <tbody>
                ${sevaRows.length ? sevaRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(String(row.seva_date || row.booking_date || row.date || "").slice(0, 10))}</td>
                    <td>${escapeHtml(row.seva_name || "Seva")}</td>
                    <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                    <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    <td>${escapeHtml(row.status || "")}</td>
                  </tr>
                `).join("") : `<tr><td colspan="5">No seva bookings for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Seva Schedule</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Seva</th><th>Devotee</th><th>Phone</th></tr>
              </thead>
              <tbody>
                ${scheduleRows.length ? scheduleRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(String(row.date || row.booking_date || "").slice(0, 10))}</td>
                    <td>${escapeHtml(row.seva_name || "Seva")}</td>
                    <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                    <td>${escapeHtml(row.devotee_mobile || row.devotee_phone || "")}</td>
                  </tr>
                `).join("") : `<tr><td colspan="4">No upcoming seva schedule rows.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>80G Readiness</h4>
          <p class="muted">Readiness evidence only; this is not an official certificate or filing.</p>
          <div class="table-preview compact-table">
            <table>
              <thead><tr><th>Receipt</th><th>Donor</th><th>PAN</th><th>Status</th></tr></thead>
              <tbody>
                ${rows80g.length ? rows80g.slice(0, 8).map((row) => `
                  <tr><td>${escapeHtml(row.receipt_number || row.donation_id || "")}</td><td>${escapeHtml(row.devotee_name || "Devotee")}</td><td>${escapeHtml(row.donor_pan_masked || "Not provided")}</td><td>${escapeHtml(row["80g_eligibility_status"] || "not_requested")}</td></tr>
                `).join("") : `<tr><td colspan="4">No 80G readiness records for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>FCRA Readiness</h4>
          <p class="muted">Foreign-contribution readiness evidence only; this is not an official filing.</p>
          <div class="table-preview compact-table">
            <table>
              <thead><tr><th>Receipt</th><th>Donor</th><th>Country</th><th>Status</th></tr></thead>
              <tbody>
                ${rowsFcra.length ? rowsFcra.slice(0, 8).map((row) => `
                  <tr><td>${escapeHtml(row.receipt_number || row.donation_id || "")}</td><td>${escapeHtml(row.devotee_name || "Devotee")}</td><td>${escapeHtml(row.donor_country || "Not provided")}</td><td>${escapeHtml(row.fcra_status || "not_applicable")}</td></tr>
                `).join("") : `<tr><td colspan="4">No FCRA readiness records for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
      </div>
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Fund and Inventory Drill-down</h4>
            <p>Read-only evidence derived from posted fund dimensions and append-only inventory movements.</p>
          </div>
          <span class="pill">Accounting-backed</span>
        </div>
        <div class="metric-grid four">${renderStatCards([
          ["Fund Closing Balance", formatCurrency(fundSubledger.totals?.closing_balance || 0), `${fundRows.length} funds`],
          ["Fund Donations", formatCurrency(fundWise.total_amount || 0), formatCountLabel(fundWise.total_count || 0, "receipt")],
          ["Inventory Value", formatCurrency(inventorySummary.totalValue || 0), `${inventoryRows.length} active items`],
          ["Inventory Approvals", pendingInventoryApprovals, "pending maker-checker review"],
        ])}</div>
        <div class="dashboard-main-grid platform-grid">
          <article>
            <h4>Fund Subledger</h4>
            <div class="table-preview compact-table">
              <table>
                <thead><tr><th>Fund</th><th>Type</th><th class="amount">Opening</th><th class="amount">Income</th><th class="amount">Expense</th><th class="amount">Transfers In</th><th class="amount">Transfers Out</th><th class="amount">Closing</th></tr></thead>
                <tbody>
                  ${fundRows.length ? fundRows.slice(0, 12).map((row) => `
                    <tr><td>${escapeHtml(row.fund_name || row.fund_id || "")}</td><td>${escapeHtml(row.fund_type || "")}</td><td class="amount">${escapeHtml(formatCurrency(row.opening_balance || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.income || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.expense || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.transfers_in || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.transfers_out || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.closing_balance || 0))}</td></tr>
                  `).join("") : `<tr><td colspan="8">No accounting-backed fund activity for this range.</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
          <article>
            <h4>Designated Collections</h4>
            <div class="table-preview compact-table">
              <table>
                <thead><tr><th>Designation</th><th>Kind</th><th>Count</th><th class="amount">Amount</th></tr></thead>
                <tbody>
                  ${[
                    ...fundDonationRows.map((row) => ({ ...row, kind: "Fund" })),
                    ...festivalDonationRows.map((row) => ({ ...row, kind: "Festival" })),
                  ].slice(0, 12).map((row) => `<tr><td>${escapeHtml(row.name || row.id || "")}</td><td>${escapeHtml(row.kind)}</td><td>${escapeHtml(row.count || 0)}</td><td class="amount">${escapeHtml(formatCurrency(row.amount || 0))}</td></tr>`).join("") || `<tr><td colspan="4">No designated collections for this range.</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
          <article>
            <h4>Inventory Stock Valuation</h4>
            <p class="muted">Weighted-average values are derived from posted receipts, issues, and reversals.</p>
            <div class="table-preview compact-table">
              <table>
                <thead><tr><th>Item</th><th class="amount">On Hand</th><th class="amount">Average Value</th><th class="amount">Stock Value</th><th>Status</th></tr></thead>
                <tbody>
                  ${inventoryRows.length ? inventoryRows.slice(0, 12).map((row) => `
                    <tr><td>${escapeHtml([row.item_code, row.item_name].filter(Boolean).join(" - "))}</td><td class="amount">${escapeHtml(`${row.on_hand_qty || "0.000"} ${row.unit || ""}`.trim())}</td><td class="amount">${escapeHtml(formatCurrency(row.weighted_average_unit_value || 0))}</td><td class="amount">${escapeHtml(formatCurrency(row.on_hand_value || 0))}</td><td>${row.reorder_required ? '<span class="status-badge danger">Reorder</span>' : '<span class="status-badge success">Available</span>'}</td></tr>
                  `).join("") : `<tr><td colspan="5">${reports.inventory_enabled ? "No active inventory items." : "Inventory accounting is off for this tenant."}</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
          <article>
            <h4>Inventory Audit Trail</h4>
            <div class="table-preview compact-table">
              <table>
                <thead><tr><th>Date</th><th>Item</th><th>Movement</th><th class="amount">Quantity</th><th class="amount">Value</th><th>Status</th></tr></thead>
                <tbody>
                  ${inventoryMovements.length ? inventoryMovements.slice(0, 12).map((row) => `
                    <tr><td>${escapeHtml(String(row.movement_date || row.created_at || "").slice(0, 10))}</td><td>${escapeHtml(row.item_name || row.item_id || "")}</td><td>${escapeHtml(row.movement_type || "")}</td><td class="amount">${escapeHtml(row.quantity || "0.000")}</td><td class="amount">${escapeHtml(formatCurrency(row.total_value || 0))}</td><td>${escapeHtml(row.status || "")}</td></tr>
                  `).join("") : `<tr><td colspan="6">No append-only inventory movements.</td></tr>`}
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </div>
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Recent Devotees</h4>
            <p>Tenant-scoped devotee records captured from donations, sevas, and public payments.</p>
          </div>
          <span class="pill">${devotees.length} shown</span>
        </div>
        <div class="table-preview compact-table">
          <table>
            <thead>
              <tr><th>Name</th><th>Phone</th><th>City</th><th>Updated</th></tr>
            </thead>
            <tbody>
              ${devotees.length ? devotees.slice(0, 12).map((row) => `
                <tr>
                  <td>${escapeHtml(row.name || row.first_name || "Devotee")}</td>
                  <td>${escapeHtml(row.phone || row.mobile || "")}</td>
                  <td>${escapeHtml(row.city || "")}</td>
                  <td>${escapeHtml(String(row.updated_at || row.created_at || "").slice(0, 10))}</td>
                </tr>
              `).join("") : `<tr><td colspan="4">No devotee records found.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderMandirDevoteesView(reports = lastMandirOperationalReports) {
  const devotees = Array.isArray(reports.devotees) ? reports.devotees : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Devotees</h4>
          <p>Tenant-scoped devotee records captured from donations, sevas, and public payments.</p>
        </div>
        <span class="pill">${devotees.length} shown</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Name</th><th>Phone</th><th>City</th><th>Updated</th></tr>
          </thead>
          <tbody>
            ${devotees.length ? devotees.slice(0, 20).map((row) => `
              <tr>
                <td>${escapeHtml(row.name || row.first_name || "Devotee")}</td>
                <td>${escapeHtml(row.phone || row.mobile || "")}</td>
                <td>${escapeHtml(row.city || "")}</td>
                <td>${escapeHtml(String(row.updated_at || row.created_at || "").slice(0, 10))}</td>
              </tr>
            `).join("") : `<tr><td colspan="4">No devotee records found.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — dashboard home + workspace tabs
// API   : GET /api/v1/mandir/dashboard
// NOTE  : renderMandirDashboardHome, renderMandirDashboard, renderMandirSettings
// ══════════════════════════════════════════════════════════════════════

function renderMandirDashboardHome(payload = {}) {
  const pendingPayments = Array.isArray(payload.pending_payments) ? payload.pending_payments : [];
  const paymentExceptions = Array.isArray(payload.payment_exceptions) ? payload.payment_exceptions : [];
  const recentReceipts = Array.isArray(payload.recent_receipts) ? payload.recent_receipts : [];
  const panchang = payload.panchang || null;
  const panchangPayload = panchang && panchang.ok !== false ? panchang : {};
  const gregorianDate = panchangPayload.date?.gregorian || {};
  const panchangData = panchangPayload.panchang || {};
  const sunMoon = panchangPayload.sun_moon || {};
  return `
    <div class="dashboard-main-grid platform-grid mandir-home-grid">
      <article>
        <h4>Quick Donation Entry</h4>
        <p class="muted">Use Donations for full receipt entry and sponsorship details.</p>
        <button type="button" data-workspace-view="donations">Open Donations</button>
      </article>
      <article class="panchang-card">
        <h4>Today's Panchang</h4>
        <p>${escapeHtml(gregorianDate.formatted || gregorianDate.date || "Today")}</p>
        <dl>
          <dt>Tithi</dt>
          <dd>${escapeHtml(panchangData.tithi?.full_name || panchangData.tithi?.name || "--")}</dd>
          <dt>Nakshatra</dt>
          <dd>${escapeHtml(panchangData.nakshatra?.name || "--")}</dd>
          <dt>Sunrise</dt>
          <dd>${escapeHtml(sunMoon.sunrise || "--")}</dd>
          <dt>Sunset</dt>
          <dd>${escapeHtml(sunMoon.sunset || "--")}</dd>
        </dl>
        <button type="button" class="secondary" data-workspace-view="panchang">View Full Panchang</button>
      </article>
      <article>
        <h4>Public Payment Review</h4>
        <div class="metric-grid two">${renderStatCards([
          ["Pending", pendingPayments.length, "UPI payments"],
          ["Exceptions", paymentExceptions.length, "need review"],
        ])}</div>
        <button type="button" class="secondary" data-workspace-view="payments">Open Public Payments</button>
      </article>
      <article>
        <h4>Recent Receipts</h4>
        <p class="muted">${formatCountLabel(recentReceipts.length, "receipt")} available in receipt history.</p>
        <button type="button" class="secondary" data-workspace-view="receipts">Open Receipts</button>
      </article>
    </div>
  `;
}

function renderMandirDashboard(payload = {}) {
  const stats = payload.stats || {};
  const pendingPayments = Array.isArray(payload.pending_payments) ? payload.pending_payments : [];
  const receipt = payload.receipt || null;
  const formResult = payload.form_result || null;
  const recentReceipts = Array.isArray(payload.recent_receipts) ? payload.recent_receipts : [];
  const recentDonations = Array.isArray(payload.recent_donations) ? payload.recent_donations : [];
  const recentSevaBookings = Array.isArray(payload.recent_seva_bookings) ? payload.recent_seva_bookings : [];
  const recentExpenses = Array.isArray(payload.recent_expenses) ? payload.recent_expenses : [];
  const trialBalance = payload.trial_balance || mandirReportState.trialBalance;
  const financialReports = payload.financial_reports || mandirReportState.financialReports;
  const panchang = payload.panchang || lastMandirPanchang;
  const operationalReports = payload.operational_reports || lastMandirOperationalReports;
  const paymentExceptions = Array.isArray(payload.payment_exceptions) ? payload.payment_exceptions : [];
  const paymentExceptionSummary = payload.payment_exception_summary || {};
  const donations = stats.donations || {};
  const sevas = stats.sevas || {};
  const donationCards = [
    ["Today's Donation", formatCurrency(donations.today?.amount), formatCountLabel(donations.today?.count, "donation")],
    ["Cumulative for Month", formatCurrency(donations.month?.amount), formatCountLabel(donations.month?.count, "donation")],
    ["Cumulative for Year", formatCurrency(donations.year?.amount), formatCountLabel(donations.year?.count, "donation")],
  ];
  const sevaCards = [
    ["Today's Seva", formatCurrency(sevas.today?.amount), formatCountLabel(sevas.today?.count, "booking")],
    ["Cumulative for Month", formatCurrency(sevas.month?.amount), formatCountLabel(sevas.month?.count, "booking")],
    ["Cumulative for Year", formatCurrency(sevas.year?.amount), formatCountLabel(sevas.year?.count, "booking")],
  ];
  const showOverview = activeMandirWorkspace === "overview";
  const showDonations = activeMandirWorkspace === "donations";
  const showSevas = ["sevas", "book-sevas", "seva-bookings", "seva-management", "reschedule-approval"].includes(activeMandirWorkspace);
  const showDevotees = activeMandirWorkspace === "devotees";
  const showPayments = activeMandirWorkspace === "payments";
  const showExceptions = activeMandirWorkspace === "exceptions";
  const showReceipts = activeMandirWorkspace === "receipts";
  const showPanchang = activeMandirWorkspace === "panchang";
  const showReports = activeMandirWorkspace === "reports";
  const showAccounting = activeMandirWorkspace === "accounting";
  const showSettings = activeMandirWorkspace === "settings";
  const showImplementation = activeMandirWorkspace === "implementation";
  const showPlatformOwners = activeMandirWorkspace === "platform-owners";
  const pageMeta = {
    overview: ["Dashboard", "Donation, seva, public payment review, and today's panchang for the active temple tenant."],
    donations: ["Donations", "Record and review donation receipts for the active temple tenant."],
    sevas: ["Sevas", "Book and review seva receipts for the active temple tenant."],
    "book-sevas": ["Book Sevas", "Create seva bookings for devotees."],
    "seva-bookings": ["Seva Bookings / Reschedule", "Review bookings and reschedule requests."],
    "seva-management": ["Seva Management", "Manage seva definitions and temple service workflows."],
    "reschedule-approval": ["Reschedule Approval", "Approve or reject seva reschedule requests."],
    devotees: ["Devotees", "Tenant-scoped devotee records captured from donations, sevas, and public payments."],
    payments: ["Public Payments", "Verify no-login UPI payments before posting receipts and accounting."],
    exceptions: ["Payment Exceptions", "Review public payment records that need correction or rejection."],
    receipts: ["Receipts", "Preview, download, and reverse donation or seva receipts."],
    panchang: ["Panchang", "Temple calendar and panchang visibility."],
    reports: ["Reports", "Donation, seva, devotee, and operational reports."],
    accounting: ["Accounting", "Trial Balance, drill-down, financial reports, and temple expenses."],
    settings: ["Settings", "Tenant-level MandirMitra configuration and safety controls."],
    implementation: ["Implementation Checks", "First-live checklist and deployment readiness tracking."],
    "platform-owners": ["Platform Owners", "Privileged platform-owner administration shortcut."],
  }[activeMandirWorkspace] || ["Dashboard", "MandirMitra temple workspace."];

  return `
    <div class="legacy-dashboard mandir-dashboard">
      <div class="preview-heading">
        <div>
          <h3>${escapeHtml(pageMeta[0])}</h3>
          <p>${escapeHtml(pageMeta[1])}</p>
        </div>
        <span class="pill ok technical-context">mandirmitra</span>
      </div>
      ${isProductionShell() && isMandirHost() ? "" : renderMandirWorkspaceTabs(activeMandirWorkspace)}
      ${renderMandirOperationResult(formResult)}
      ${(showOverview || activeMandirWorkspace === "donations") ? `
        <h4>Donations</h4>
        <div class="metric-grid three">${renderStatCards(donationCards)}</div>
      ` : ""}
      ${(showOverview || showSevas) ? `
        <h4>Sevas</h4>
        <div class="metric-grid three">${renderStatCards(sevaCards)}</div>
      ` : ""}
      ${showOverview ? renderMandirDashboardHome({
        pending_payments: pendingPayments,
        payment_exceptions: paymentExceptions,
        recent_receipts: recentReceipts,
        panchang,
      }) : ""}
      ${(showDonations || showSevas) ? `
        ${renderMandirCreateForms({
          payment_accounts: payload.payment_accounts,
          accounts: payload.accounts,
          module_config: payload.module_config,
          compliance_config: payload.compliance_config,
          form_result: null,
        })}
        <div class="dashboard-main-grid ${showOverview ? "platform-grid" : ""}">
          ${showDonations ? `
        <article>
          <h4>${showOverview ? "Recent Donations" : "Donations"}</h4>
          ${renderMandirListFilters("donations", recentDonations.length)}
          ${renderMandirDonationsTable(recentDonations)}
        </article>
          ` : ""}
          ${showSevas ? `
        <article>
          <h4>${showOverview ? "Recent Seva Bookings" : "Seva Bookings"}</h4>
          ${renderMandirListFilters("sevas", recentSevaBookings.length)}
          ${renderMandirSevaBookingsTable(recentSevaBookings)}
        </article>
          ` : ""}
        </div>
      ` : ""}
      ${showDevotees ? renderMandirDevoteesView(operationalReports) : ""}
      ${showPayments ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Public Payments Pending Verification</h4>
            <p>Verify UPI payments only after temple staff confirms the payment, then post receipt and accounting.</p>
          </div>
          <div class="action-row">
            <a class="button secondary" href="${escapeHtml(mandirPublicPaymentPageUrl())}" target="_blank" rel="noopener">Open Public Page</a>
            <span class="pill warn">${pendingPayments.length} pending</span>
          </div>
        </div>
        ${renderMandirPublicPaymentFilters(pendingPayments.length)}
        ${renderMandirPublicPaymentsTable(pendingPayments)}
      </div>
      ` : ""}
      ${showExceptions ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Payment Exceptions</h4>
            <p>Old pending payments and invalid public payment records that need staff review.</p>
          </div>
          <span class="pill warn">${escapeHtml(paymentExceptionSummary.total || paymentExceptions.length)} flagged</span>
        </div>
        ${renderMandirExceptionFilters(paymentExceptions.length)}
        ${renderMandirExceptionsTable(paymentExceptions)}
      </div>
      ` : ""}
      ${showReceipts ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Recent Receipts</h4>
            <p>Donation and seva receipts generated for this temple tenant.</p>
          </div>
          <span class="pill">${recentReceipts.length} shown</span>
        </div>
        ${renderMandirReceiptHistoryTable(recentReceipts)}
      </div>
      ` : ""}
      ${showReceipts && receipt ? `
        <div class="verification-panel">
          <div class="preview-heading compact">
            <div>
              <h4>Last Verified Receipt</h4>
              <p>${escapeHtml(receipt.receipt_number || receipt.source_id || "Receipt ready")}</p>
            </div>
            <div class="action-row">
              <button
                class="secondary"
                type="button"
                data-mandir-action="preview-receipt"
                data-receipt-url="${escapeHtml(receipt.receipt_pdf_url)}"
                data-receipt-label="${escapeHtml(receipt.receipt_number || receipt.source_id || "Receipt")}"
              >Preview</button>
              <button
                type="button"
                data-mandir-action="download-receipt"
                data-receipt-url="${escapeHtml(receipt.receipt_pdf_url)}"
                data-receipt-filename="${escapeHtml(receipt.filename)}"
              >Download Receipt</button>
            </div>
          </div>
        </div>
      ` : ""}
      ${showPanchang ? renderMandirPanchang(panchang) : ""}
      ${showReports ? renderMandirOperationalReports(operationalReports) : ""}
      ${showSettings ? renderMandirSettings(payload.module_config || {}, payload.compliance_config || {}) : ""}
      ${showImplementation ? renderMandirImplementationChecks() : ""}
      ${showPlatformOwners ? renderMandirPlatformOwnerShortcut() : ""}
      ${showAccounting ? renderAccountingDrilldownPanel() : ""}
      ${showAccounting ? renderMandirTrialBalance(trialBalance) : ""}
      ${showAccounting ? renderMandirFinancialReports(financialReports) : ""}
      ${showAccounting ? renderMandirExpensesTable(recentExpenses) : ""}
    </div>
  `;
}

function renderMandirSettings(moduleConfig = {}, complianceConfig = {}) {
  const inventoryEnabled = Boolean(moduleConfig.module_inventory_enabled ?? moduleConfig.inventory_enabled);
  const flags = [
    ["Inventory accounting", inventoryEnabled ? "Enabled" : "Disabled", inventoryEnabled ? "In-kind consumables can debit inventory where configured." : "In-kind consumables debit expense unless the tenant enables inventory."],
    ["80G", moduleConfig.enable_80g ? "Enabled" : "Off", "Tenant-configured only; never default-on."],
    ["FCRA", moduleConfig.enable_fcra ? "Enabled" : "Off", "Tenant-configured only; never default-on."],
    ["Receipt reversal", "Enabled", "Corrections are handled by linked reversal journals."],
  ];
  return `
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Settings</h4>
        <div class="metric-grid two">
          ${flags.map(([label, value, subtext]) => `
            <article class="metric-tile">
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(value)}</strong>
              <small>${escapeHtml(subtext)}</small>
            </article>
          `).join("")}
        </div>
      </article>
      <article>
        <h4>Tenant Controls</h4>
        <ul class="activity-list">
          ${renderActivity([
            "UPI/payee visibility comes from temple configuration.",
            "Donation, seva, and expense postings go through MitraBooks accounting.",
            "Public payments remain pending until staff verification.",
            "Real trusts must not be used for destructive smoke tests.",
          ])}
        </ul>
      </article>
      <article class="verification-panel">
        <h4>Donation Compliance</h4>
        <p class="muted">Default-off tenant configuration. Save only after the trust's legal/compliance reviewer verifies the approval evidence.</p>
        <form class="entry-form" data-mandir-compliance-form>
          <label class="field"><span><input name="enable_80g" type="checkbox" ${complianceConfig.enable_80g ? "checked" : ""}> Enable 80G readiness</span></label>
          <label class="field"><span>Institution PAN</span><input name="institution_pan" maxlength="10" value="${escapeHtml(complianceConfig.institution_pan || "")}" placeholder="ABCDE1234F"></label>
          <label class="field"><span>Approval number</span><input name="approval_number" maxlength="120" value="${escapeHtml(complianceConfig.approval_number || "")}"></label>
          <label class="field"><span>Approval valid from</span><input name="approval_valid_from" type="date" value="${escapeHtml(complianceConfig.approval_valid_from || "")}"></label>
          <label class="field"><span>Approval valid to</span><input name="approval_valid_to" type="date" value="${escapeHtml(complianceConfig.approval_valid_to || "")}"></label>
          <label class="field"><span>Certificate label</span><input name="certificate_label" maxlength="120" value="${escapeHtml(complianceConfig.certificate_label || "Donation certificate")}"></label>
          <label class="field"><span>Cash eligibility limit</span><input name="cash_eligibility_limit" type="number" min="0.01" step="0.01" value="${escapeHtml(complianceConfig.cash_eligibility_limit || "")}"></label>
          <label class="field"><span>Cash rule effective from</span><input name="cash_rule_effective_from" type="date" value="${escapeHtml(complianceConfig.cash_rule_effective_from || "")}"></label>
          <label class="field"><span>Receipt disclaimer</span><textarea name="receipt_disclaimer" maxlength="500">${escapeHtml(complianceConfig.receipt_disclaimer || "")}</textarea></label>
          <label class="field"><span><input name="enable_fcra" type="checkbox" ${complianceConfig.enable_fcra ? "checked" : ""}> Enable FCRA readiness</span></label>
          <label class="field"><span>FCRA approval type</span><select name="fcra_registration_type"><option value="registration" ${complianceConfig.fcra_registration_type === "registration" ? "selected" : ""}>Registration</option><option value="prior_permission" ${complianceConfig.fcra_registration_type === "prior_permission" ? "selected" : ""}>Prior permission</option></select></label>
          <label class="field"><span>FCRA reference</span><input name="fcra_registration_number" maxlength="120" value="${escapeHtml(complianceConfig.fcra_registration_number || "")}"></label>
          <label class="field"><span>FCRA valid from</span><input name="fcra_valid_from" type="date" value="${escapeHtml(complianceConfig.fcra_valid_from || "")}"></label>
          <label class="field"><span>FCRA valid to</span><input name="fcra_valid_to" type="date" value="${escapeHtml(complianceConfig.fcra_valid_to || "")}"></label>
          <label class="field"><span>Designated account ID</span><input name="fcra_designated_account_id" maxlength="120" value="${escapeHtml(complianceConfig.fcra_designated_account_id || "")}" placeholder="Use this account during foreign donation entry"></label>
          <button type="submit">Save Compliance Configuration</button>
        </form>
      </article>
    </div>
  `;
}

function renderMandirImplementationChecks() {
  return `
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Implementation Checks</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Donation and seva receipt PDFs are generated and downloadable.",
            "Donation, seva, expense, sponsorship, and reversal postings use double-entry journals.",
            "Trial Balance, Income & Expenditure, Receipts & Payments, and Balance Sheet remain balanced.",
            "Tenant and app context come from the access token and X-App-Key.",
            "Public payment page is no-login, but posting requires staff verification.",
          ])}
        </ul>
      </article>
      <article>
        <h4>First-live Pending Areas</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Full legacy screen-by-screen UI migration is still incremental.",
            "Production backup/restore and release rollback runbook must stay current.",
            "Panchang needs the next feature-complete pass after first-live shell stabilization.",
          ])}
        </ul>
      </article>
    </div>
  `;
}

function renderMandirPlatformOwnerShortcut() {
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Platform Owners</h4>
          <p>Platform-owner administration remains a separate privileged workspace.</p>
        </div>
        <button type="button" class="secondary" data-platform-action="open-platform-owner">Open Platform Owner</button>
      </div>
      <p class="muted">Use this only with a super-admin token. Tenant admins should stay inside the MandirMitra workspace.</p>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: DASHBOARD PREVIEW SHELL
// NOTE  : renderDashboardPreview — outermost wrapper rendered into dashboardPreview element
// ══════════════════════════════════════════════════════════════════════

function renderDashboardPreview(config) {
  const dashboard = config.dashboard;
  if (!dashboard) {
    return "";
  }

  if (dashboard.type === "platform") {
    return renderPlatformDashboard(lastPlatformOwnerDashboard || emptyPlatformDashboardPayload());
  }

  if (dashboard.type === "mandir") {
    return `
      <div class="legacy-dashboard mandir-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Dashboard</h3>
            <p>Old MandirMitra pattern with separate donation, seva, and public payment verification summaries.</p>
          </div>
          <span class="pill ok">temple workspace</span>
        </div>
        <h4>Donations</h4>
        <div class="metric-grid three">${renderStatCards(dashboard.donations)}</div>
        <h4>Sevas</h4>
        <div class="metric-grid three">${renderStatCards(dashboard.sevas)}</div>
        <div class="verification-panel">
          <div class="preview-heading compact">
            <div>
              <h4>Public Payments Pending Verification</h4>
              <p>Devotee no-login UPI payments stay pending until temple staff verify and post them.</p>
            </div>
            <span class="pill warn">manual review</span>
          </div>
          <div class="metric-grid three">${renderStatCards(dashboard.verification)}</div>
        </div>
        <div class="grouped-nav-preview">
          ${dashboard.groups.map(([title, copy]) => `<article><strong>${title}</strong><span>${copy}</span></article>`).join("")}
        </div>
      </div>
    `;
  }

  if (dashboard.type === "gruha") {
    return renderGruhaDashboard(config, lastGruhaData);
  }

  if (dashboard.type === "business" || currentExperience === "mitrabooks") {
    if (activeBusinessWorkspace !== "overview") {
      return renderBusinessWorkspace();
    }
    if (activeOrgSelectorType() !== "BUSINESS") {
      return renderSelectedOrgWorkspace();
    }
    const ds = lastBusinessDashboardStats || {};
    const cashMetric = formatCurrency(Number(ds.cash_and_bank || 0));
    const recvMetric = formatCurrency(Number(ds.receivables || 0));
    const payMetric = formatCurrency(Number(ds.payables || 0));
    const gstMetric = ds.gst?.status || "—";
    return `
      <div class="business-dashboard-clean">
        ${renderBusinessExecutiveDashboard()}

        <div class="business-quick-actions-clean">
          <button class="quick-action-btn" type="button" data-business-action="open-create-voucher" title="Post a journal entry" aria-keyshortcuts="Control+Alt+V">
            <span class="quick-icon">📝</span>
            <span>Journal</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="open-create-party" title="Add a new party">
            <span class="quick-icon">👤</span>
            <span>Party</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="accounting" title="View trial balance">
            <span class="quick-icon">📊</span>
            <span>Trial Balance</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="audit" title="View audit trail">
            <span class="quick-icon">📋</span>
            <span>Audit</span>
          </button>
        </div>

        <div class="business-bottom-metrics">
          <div class="metric-item">
            <span class="metric-label">Cash and Bank</span>
            <strong class="metric-value">${escapeHtml(cashMetric)}</strong>
            <small class="metric-sub">available balance</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Receivables</span>
            <strong class="metric-value">${escapeHtml(recvMetric)}</strong>
            <small class="metric-sub">open invoices</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Payables</span>
            <strong class="metric-value">${escapeHtml(payMetric)}</strong>
            <small class="metric-sub">vendor dues</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">GST Filing</span>
            <strong class="metric-value">${escapeHtml(gstMetric)}</strong>
            <small class="metric-sub">current period</small>
          </div>
        </div>

        <div class="business-recent-activity-clean">
          <h4>Recent Activity</h4>
          <ul class="activity-list">${renderActivity(dashboard.activity || [])}</ul>
        </div>
      </div>
    `;
}
}

// ========== Business Module: Party Master ==========

let activeBusinessWorkspace = "overview";
let lastBusinessPartiesResult = null;
let activeSettingsDetailId = "";
let lastBusinessAdminSettings = null;

const MITRABOOKS_SETTINGS_GROUPS = [
  {
    title: "Core Settings",
      description: "Always visible for MitraBooks business tenants.",
      items: [
      { title: "Organization", status: "Implemented", detail: "Tenant-scoped legal name, trade name, tax IDs, contact details, financial year, currency, time zone, and logo settings save through MitraBooks admin settings.", visibility: "Owner, Admin, CA Partner" },
      { title: "Branches", status: "Implemented", detail: "Branch code, GST registration per branch, address, warehouse mapping, and cost centre mapping now save in tenant-scoped MitraBooks admin settings.", visibility: "Multi-location businesses" },
      { title: "Users & Roles", status: "Implemented", detail: "Tenant-scoped role templates for Owner, Admin, Accountant, Cashier, Auditor, and Viewer now save through MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Permissions", status: "Implemented", detail: "Tenant-scoped module and action permission templates for approvals, reports, banking, inventory, and settings now save through MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Chart of Accounts", status: "Implemented", detail: "Default business chart, protected system accounts, ledger drill-down, and opening balances through journal posting.", visibility: "Accounting users", workspace: "accounting" },
      { title: "Tax & Compliance", status: "Implemented", detail: "GST registration mode, GST reports, GSTR preparation, TDS/TCS sections, period locks, and reconciliation workflows.", visibility: "Accountant, CA", workspace: "gst-returns" },
      { title: "Voucher Configuration", status: "Implemented", detail: "Voucher prefixes, approval threshold, and default approver role now save in tenant-scoped MitraBooks admin settings, while posting workflows remain in the vouchers workspace.", visibility: "Owner, Admin, Accountant" },
      { title: "Security", status: "Implemented", detail: "MFA requirement, password policy floor, session timeout, concurrent-session rule, and login alert email now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Module Settings",
    description: "Visible when the corresponding MitraBooks module or business mode is enabled.",
    items: [
      { title: "Invoice Settings", status: "Implemented", detail: "Sales invoice fields, numbering pattern, GST registration type, composition category, and inventory accounting toggle.", visibility: "Admin", workspace: "sales" },
      { title: "Inventory", status: "Partial", detail: "Item master and stock register exist. UOM, godowns, valuation policy, and stock approvals are planned.", visibility: "Inventory businesses", workspace: "reports" },
      { title: "Banking", status: "Partial", detail: "Manual bank reconciliation exists. Bank account setup, gateway mapping, and bank API sync are planned.", visibility: "Banking users", workspace: "bank-recon" },
      { title: "Financial Controls", status: "Implemented", detail: "Voucher lock date, backdated-entry approval, locked-period override policy, and period-close note now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Auditor" },
      { title: "Templates", status: "Implemented", detail: "Invoice, receipt, payment voucher, statement, and report template choices with footer branding now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Notifications", status: "Implemented", detail: "Email, SMS, WhatsApp, due-date, approval, and compliance reminder rules now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Professional Practice Settings",
    description: "For CA firms and bookkeepers handling many client companies from one login.",
    items: [
      { title: "Client Management", status: "Implemented", detail: "Tenant-scoped CA client records capture GSTIN/PAN, contact person, engagement type, notes, and active status through the CA Practice Portal.", visibility: "CA Partner, Practice Admin", workspace: "ca-access" },
      { title: "Multi-Company Dashboard", status: "Implemented", detail: "CA Practice Portal lists client books and supports quick company switching into the filtered review queue.", visibility: "CA Partner, Staff", workspace: "ca-access" },
      { title: "Client Access Control", status: "Implemented", detail: "Client records save scoped access levels such as view only, data entry, full access, and restricted filing visibility.", visibility: "CA Partner", workspace: "ca-access" },
      { title: "Compliance Tracking", status: "Implemented", detail: "CA client records plus document metadata track GST, TDS, income tax, audit, ROC, and bookkeeping compliance queues.", visibility: "CA Partner, Staff", workspace: "ca-access" },
      { title: "Work Assignment", status: "Implemented", detail: "Clients and CA document metadata both capture owner and assignee fields for practice workload routing.", visibility: "Practice Admin", workspace: "ca-access" },
    ],
  },
  {
    title: "Platform Settings",
    description: "Controlled settings for subscription, integrations, audit, and AI enablement.",
    items: [
      { title: "Subscription & Billing", status: "Implemented", detail: "Billing contacts, invoice delivery email, renewal mode, and payment provider preference now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Platform Admin" },
      { title: "Integrations", status: "Implemented", detail: "Tenant-scoped integration shells now save payment gateway, GST portal, bank feed, WhatsApp, email, and document storage settings without exposing provider secrets to the frontend.", visibility: "Owner, Admin" },
      { title: "Audit & Logs", status: "Implemented", detail: "Party, voucher, account, document, and lifecycle events are visible through audit trail.", visibility: "Owner, Auditor", workspace: "audit" },
      { title: "AI Settings", status: "Implemented", detail: "Tenant-scoped AI/OCR controls now save review-first settings for OCR, categorization, reconciliation assistance, MIS, and forecasting. Auto-post to ledger remains disabled.", visibility: "Owner, Admin" },
    ],
  },
];

const MITRABOOKS_COMPLETION_PHASES = [
  ["Phase 2A", "Jun 12-14", "Landing pricing, shared SanMitra Razorpay configuration, billing metadata"],
  ["Phase 2B", "Jun 15-21", "Core settings backend contracts and tenant-scoped saves"],
  ["Phase 2C", "Jun 22-30", "CA practice client onboarding, multi-company access, and work queues"],
  ["Phase 2D", "Jul 1-12", "Integrations, document storage, OCR, AI settings, and provider controls"],
  ["Phase 2E", "Jul 13-19", "Browser E2E, tenant isolation, accounting guardrails, and staging validation"],
];

function settingsItemId(item) {
  return String(item.title || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function allMitraBooksSettingsItems() {
  return MITRABOOKS_SETTINGS_GROUPS.flatMap((group) =>
    group.items.map((item) => ({ ...item, groupTitle: group.title })),
  );
}

function findMitraBooksSettingsItem(settingId) {
  return allMitraBooksSettingsItems().find((item) => settingsItemId(item) === settingId) || null;
}

const BUSINESS_ADMIN_SETTINGS_SECTION_KEYS = {
  "organization": "organization",
  "branches": "branches",
  "users-and-roles": "roles",
  "permissions": "permissions",
  "voucher-configuration": "voucher_configuration",
  "financial-controls": "financial_controls",
  "security": "security",
  "templates": "templates",
  "notifications": "notifications",
  "subscription-and-billing": "subscription_billing",
  "integrations": "integrations",
  "ai-settings": "ai_settings",
};

function businessAdminSettingsSectionKey(settingId) {
  return BUSINESS_ADMIN_SETTINGS_SECTION_KEYS[settingId] || "";
}

function buildBusinessAdminSettingsPayload(source = {}) {
  return {
    organization: source.organization || {},
    branches: Array.isArray(source.branches) ? source.branches : [],
    roles: Array.isArray(source.roles) ? source.roles : [],
    permissions: source.permissions || { module_permissions: {}, action_permissions: {} },
    voucher_configuration: source.voucher_configuration || {},
    financial_controls: source.financial_controls || {},
    security: source.security || {},
    templates: source.templates || {},
    notifications: source.notifications || {},
    subscription_billing: source.subscription_billing || {},
    integrations: source.integrations || {},
    ai_settings: source.ai_settings || {},
    accounting_entity_id: "primary",
  };
}

const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",
    from_date: "",
    to_date: "",
  },
  vouchers: {
    offset: 0,
    voucher_type: "",
    status: "",
    approval_status: "",
    include_reviewed: false,
  },
};


// ══════════════════════════════════════════════════════════════════════
// SECTION: PARTIES TABLE RENDERER
// NOTE  : renderBusinessPartiesTable, renderBusinessPartiesListFilters — list view only
// ══════════════════════════════════════════════════════════════════════

function renderBusinessPartiesTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No parties found</strong>
        <span>Add a customer or vendor to use party context in vouchers.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>GSTIN</th>
            <th>Balance Source</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const isInactive = row.is_inactive || row.status === "inactive";
            const partyName = row.party_name || row.name || "Unnamed";
            const balanceSource = row.balance_source === "ledger_reports" ? "Ledger reports" : "Profile";
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(partyName)}</strong>
                  <span class="row-subtext">${escapeHtml(row.party_code || row.code || "")}</span>
                </td>
                <td><span class="type-chip">${escapeHtml(row.party_type || row.type || "unknown")}</span></td>
                <td>${escapeHtml(row.gstin || "-")}</td>
                <td><span class="row-subtext">${escapeHtml(balanceSource)}</span></td>
                <td><span class="pill ${isInactive ? "warn" : "ok"}">${isInactive ? "Inactive" : "Active"}</span></td>
                <td>
                  <div class="action-row">
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="edit-party"
                      data-party-id="${escapeHtml(row.party_id || row.id || "")}"
                      data-party-name="${escapeHtml(partyName)}"
                      data-party-type="${escapeHtml(row.party_type || "customer")}"
                      data-party-gstin="${escapeHtml(row.gstin || "")}"
                      data-party-pan="${escapeHtml(row.pan || "")}"
                      data-party-city="${escapeHtml(row.city || "")}"
                      data-party-state="${escapeHtml(row.state || "")}"
                      data-party-pincode="${escapeHtml(row.pincode || "")}"
                    >Edit</button>
                    ${!isInactive ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="deactivate-party"
                        data-party-id="${escapeHtml(row.party_id || row.id || "")}"
                      >Deactivate</button>
                    ` : ""}
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderBusinessPartiesListFilters(rowsLength) {
  const state = businessListState.parties;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 20) : 0;
  const nextDisabled = rowsLength < 20 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="parties">
      <div class="list-filter-bar">
        <label class="field">
          <span>Search</span>
          <input name="q" type="search" value="${escapeHtml(state.q || "")}" placeholder="Name or GSTIN">
        </label>
        <label class="field">
          <span>Type</span>
          <select name="party_type">
            <option value="">All types</option>
            <option value="customer" ${state.party_type === "customer" ? "selected" : ""}>Customer</option>
            <option value="vendor" ${state.party_type === "vendor" ? "selected" : ""}>Vendor</option>
            <option value="both" ${state.party_type === "both" ? "selected" : ""}>Both</option>
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-list-filter" data-list-kind="parties">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-list-filter" data-list-kind="parties">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="parties" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="parties" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS TABLE RENDERER
// NOTE  : renderBusinessVouchersTable — list view only; full CRUD at SECTION: VOUCHERS CRUD
// ══════════════════════════════════════════════════════════════════════

function renderBusinessVouchersTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No vouchers posted yet</strong>
        <span>Post a balanced journal voucher after the chart of accounts is available.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Narration</th>
            <th>Status</th>
            <th>Approval</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const status = row.status || "posted";
            const isReversed = status === "reversed";
            const approvalStatus = row.approval_status || "not_submitted";
            const reviewer = row.approval_decided_by || row.reviewed_by || "";
            const canApprove = status === "pending_approval";
            const canReject = status === "pending_approval";
            return `
              <tr>
                <td>${escapeHtml(String(row.entry_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.reference || row.cheque_number || "-")}</td>
                <td>${escapeHtml(row.voucher_type || "journal")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit || row.amount || 0))}</td>
                <td>${escapeHtml((row.description || row.narration || "").slice(0, 40))}</td>
                <td><span class="pill ${isReversed ? "warn" : "ok"}">${escapeHtml(status)}</span></td>
                <td>
                  <span class="pill ${approvalStatus === "rejected" ? "warn" : approvalStatus === "approved" ? "ok" : ""}">${escapeHtml(approvalStatus)}</span>
                  <span class="row-subtext">${escapeHtml(reviewer || "Unreviewed")}</span>
                </td>
                <td>
                  <div class="action-row">
                    ${canApprove ? `
                      <button
                        type="button"
                        data-business-action="review-voucher-approve"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Approve</button>
                    ` : ""}
                    ${canReject ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="review-voucher-reject"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Reject</button>
                    ` : ""}
                    ${!isReversed ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="reverse-voucher"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Reverse</button>
                    ` : `
                      <button class="secondary" type="button" disabled>Reversed</button>
                    `}
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function settingsStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "implemented") return "ok";
  if (normalized === "partial") return "warn";
  return "neutral";
}

function renderMitraBooksSettingsCard(item) {
  const settingId = settingsItemId(item);
  const sectionKey = businessAdminSettingsSectionKey(settingId);
  const action = item.workspace
    ? `<button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open Related Area</button>`
    : sectionKey
      ? `<button class="secondary" type="button" data-business-action="settings-detail" data-settings-id="${escapeHtml(settingId)}">Open Setup</button>`
      : `<button class="secondary" type="button" data-business-action="settings-detail" data-settings-id="${escapeHtml(settingId)}">View Setup</button>`;
  return `
    <article class="settings-menu-card" data-settings-card="${escapeHtml(settingId)}">
      <div class="settings-card-head">
        <h5>${escapeHtml(item.title)}</h5>
        <span class="pill ${settingsStatusClass(item.status)}">${escapeHtml(item.status)}</span>
      </div>
      <p>${escapeHtml(item.detail)}</p>
      <div class="settings-card-meta">
        <span>${escapeHtml(item.visibility)}</span>
        ${action}
      </div>
    </article>
  `;
}

function renderBusinessAdminSettingsEditor(item, sectionKey) {
  const sectionValue = lastBusinessAdminSettings?.[sectionKey];
  const prettyValue = JSON.stringify(
    sectionValue ?? buildBusinessAdminSettingsPayload()[sectionKey] ?? {},
    null,
    2,
  );
  return `
    <article class="settings-json-editor">
      <strong>Tenant-scoped setup</strong>
      <p>Edit the JSON for this settings section and save it to the current MitraBooks tenant.</p>
      <textarea class="json-textarea" data-settings-json="${escapeHtml(sectionKey)}" spellcheck="false">${escapeHtml(prettyValue)}</textarea>
      <div class="settings-detail-actions">
        <button class="primary" type="button" data-business-action="save-settings-section" data-settings-section="${escapeHtml(sectionKey)}">Save ${escapeHtml(item.title)}</button>
      </div>
    </article>
  `;
}

function renderMitraBooksSettingsDetail() {
  const item = findMitraBooksSettingsItem(activeSettingsDetailId);
  if (!item) return "";
  const sectionKey = businessAdminSettingsSectionKey(activeSettingsDetailId);
  const isReady = String(item.status || "").toLowerCase() === "implemented";
  const action = item.workspace
    ? `<button class="primary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open ${escapeHtml(item.title)}</button>`
    : sectionKey
      ? ""
      : `<button class="secondary" type="button" disabled>Backend contract pending</button>`;
  const evidence = item.workspace
    ? "Available through the linked MitraBooks workspace with existing tenant-scoped route checks."
    : sectionKey
      ? "Backed by the tenant-scoped MitraBooks admin settings API."
      : "Documented as planned target scope; not yet backed by a tenant-scoped save API.";
  return `
    <section class="settings-detail-panel" data-settings-detail="${escapeHtml(activeSettingsDetailId)}">
      <div class="preview-heading compact">
        <div>
          <h5>${escapeHtml(item.title)}</h5>
          <p>${escapeHtml(item.groupTitle || "Settings")} · ${escapeHtml(item.visibility || "")}</p>
        </div>
        <span class="pill ${settingsStatusClass(item.status)}">${escapeHtml(item.status)}</span>
      </div>
      <div class="settings-detail-grid">
        <article>
          <strong>Current state</strong>
          <p>${escapeHtml(item.detail || "")}</p>
        </article>
        <article>
          <strong>${isReady ? "Verification" : "Gap"}</strong>
          <p>${escapeHtml(evidence)}</p>
        </article>
        <article>
          <strong>Deferred scope</strong>
          <p>${escapeHtml(isReady ? "No direct ledger mutation from settings; financial changes continue through controlled posting workflows." : "Final forms, permissions, audit events, and persistence will be added under the relevant backend contract.")}</p>
        </article>
      </div>
      ${sectionKey ? renderBusinessAdminSettingsEditor(item, sectionKey) : ""}
      <div class="settings-detail-actions">
        ${action}
        <button class="secondary" type="button" data-business-action="settings-back">Back to Settings</button>
      </div>
    </section>
  `;
}

function renderMitraBooksSettingsWorkspace() {
  const detail = activeSettingsDetailId ? renderMitraBooksSettingsDetail() : "";
  const settingsHealthPanel = activeSettingsDetailId ? "" : renderBusinessDataHealthPanel();
  return `
    <div class="verification-panel erp-workspace-panel mitrabooks-settings-workspace">
      <div class="preview-heading compact">
        <div>
          <h4>MitraBooks Settings</h4>
          <p>Business-only settings for accounting, compliance, controls, CA practice management, billing, integrations, and AI readiness.</p>
        </div>
        <span class="pill ok">Business suite</span>
      </div>
      <div class="settings-roadmap-strip" aria-label="MitraBooks completion roadmap">
        ${MITRABOOKS_COMPLETION_PHASES.map(([phase, date, scope]) => `
          <article>
            <strong>${escapeHtml(phase)}</strong>
            <span>${escapeHtml(date)}</span>
            <small>${escapeHtml(scope)}</small>
          </article>
        `).join("")}
      </div>
      <div class="settings-visibility-strip">
        <span><strong>Core</strong> everyone sees</span>
        <span><strong>Module</strong> shown by enabled workflow</span>
        <span><strong>Platform</strong> owner/admin controlled</span>
      </div>
      ${settingsHealthPanel}
      ${detail}
      ${MITRABOOKS_SETTINGS_GROUPS.map((group) => `
        <section class="settings-menu-section">
          <div class="settings-section-heading">
            <h5>${escapeHtml(group.title)}</h5>
            <p>${escapeHtml(group.description)}</p>
          </div>
          <div class="settings-menu-grid">
            ${group.items.map(renderMitraBooksSettingsCard).join("")}
          </div>
        </section>
      `).join("")}
      <div class="settings-boundary-note">
        <strong>Accounting guardrail:</strong>
        Live financial balances, opening balances, posted entries, tax reports, and reconciliations must continue to come from posted journals and controlled workflows. Settings must not directly mutate ledger balances.
      </div>
    </div>
  `;
}

function renderCaStatusPill(status) {
  const map = { pending: "warn", invited: "warn", accepted: "ok", revoked: "err" };
  const label = { pending: "Pending", invited: "Credentials Sent", accepted: "Active", revoked: "Revoked" };
  return `<span class="pill ${map[status] || "warn"}">${label[status] || escapeHtml(status)}</span>`;
}

function renderCaAccessManagementSection() {
  const loading = caAccessLoading ? `<p class="settings-boundary-note">Loading CA users…</p>` : "";
  const rows = caAccessUsers.length === 0 && !caAccessLoading
    ? `<tr><td colspan="5" style="text-align:center;opacity:.6">No CA users yet. Send an invite below.</td></tr>`
    : caAccessUsers.map(u => `
      <tr>
        <td>${escapeHtml(u.full_name || "—")}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${renderCaStatusPill(u.status)}</td>
        <td style="font-size:.75rem;opacity:.7">${u.invited_at ? new Date(u.invited_at).toLocaleDateString("en-IN") : "—"}</td>
        <td style="white-space:nowrap;display:flex;gap:.35rem;align-items:center">
          ${(u.status === "accepted" || u.status === "invited") && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-resend" data-ca-email="${escapeHtml(u.email)}"
              data-ca-name="${escapeHtml(u.full_name || "")}">Resend</button>
            <button class="secondary small" type="button"
              data-coa-action="ca-revoke" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Revoke</button>
          ` : u.status === "revoked" && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-reinstate" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Reinstate</button>
          ` : ""}
          ${u.invite_id ? `
            <button class="secondary small" type="button" style="color:var(--err,#f55);border-color:var(--err,#f55)"
              data-coa-action="ca-delete" data-ca-invite-id="${escapeHtml(u.invite_id)}"
              data-ca-email="${escapeHtml(u.email)}">Cancel</button>
          ` : ""}
        </td>
      </tr>`).join("");

  const successMsg = caInviteSuccess ? `<div class="pill ok" style="margin-bottom:.5rem">${escapeHtml(caInviteSuccess)}</div>` : "";
  const errMsg = caInviteError ? `<div class="pill err" style="margin-bottom:.5rem">${escapeHtml(caInviteError)}</div>` : "";

  return `
    <section class="erp-panel" style="margin-bottom:1.5rem">
      <div class="preview-heading compact" style="margin-bottom:1rem">
        <div>
          <h5>CA Access — Invited Users</h5>
          <p>CAs you invite get read-only access to financial statements, GST returns, TDS register, and bank reconciliation.</p>
        </div>
      </div>
      ${loading}
      <table class="erp-table" style="margin-bottom:1.25rem">
        <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Invited</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="settings-section-heading" style="margin-bottom:.5rem"><h6>Invite a CA</h6></div>
      ${successMsg}${errMsg}
      <form data-ca-invite-form style="display:grid;grid-template-columns:1fr 1fr auto;gap:.5rem;align-items:end">
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Name
          <input name="full_name" type="text" placeholder="e.g. CA Suresh Kumar" required maxlength="120" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Email
          <input name="email" type="email" placeholder="ca@example.com" required maxlength="120" />
        </label>
        <button type="button" data-coa-action="ca-invite-submit">Send Invite</button>
      </form>
      <p style="font-size:.75rem;opacity:.6;margin-top:.5rem">The CA receives a token-based invite email and sets the password on first use. Use <strong>Resend</strong> to issue a fresh invite link when needed.</p>
    </section>`;
}

function renderCaViewerPortal() {
  const reportLinks = [
    ["Financial Statements", "reports", "Trial Balance, P&L, Balance Sheet, General Ledger"],
    ["GST Returns", "gst-returns", "GSTR-1, GSTR-3B, GSTR-2B ITC Reconciliation"],
    ["TDS / TCS Register", "tds-tcs", "Quarterly TDS/TCS register, section-wise"],
    ["Bank Reconciliation", "bank-recon", "Statement matching and BRS"],
  ];
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Read-only access</span>
          <h4>CA Portal</h4>
          <p>You have read-only access to financial data for this business. Use the links below to navigate.</p>
        </div>
        <span class="pill ok">CA Viewer</span>
      </div>
      <div class="planned-org-module-grid">
        ${reportLinks.map(([title, workspace, copy]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <button class="secondary" type="button"
                data-business-action="workspace-view"
                data-workspace-view="${escapeHtml(workspace)}">Open</button>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>`).join("")}
      </div>
    </div>`;
}

function renderCaPracticePortalWorkspace() {
  if (isCaViewer()) {
    return renderCaViewerPortal();
  }

  const model = plannedOrgWorkspaceModel("CA_PRACTICE");
  const summary = caPracticeSummary(lastCaDocuments);
  const clients = caClientSwitchRows().slice(0, 8);
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Practice workbench</span>
          <h4>CA Practice Portal</h4>
          <p>Manage CA access to your books and track client document workflow.</p>
        </div>
        <span class="pill ok">Active</span>
      </div>
      ${isBusinessAdmin() ? renderCaAccessManagementSection() : ""}
      <div class="planned-org-kpis" style="margin-top:1rem">
        <article>
          <span>Client Tracking</span>
          <strong>${escapeHtml(String(summary.clientCount))}</strong>
          <small>Client books in this tenant queue.</small>
        </article>
        <article>
          <span>Review Queue</span>
          <strong>${escapeHtml(String(lastCaDocuments.length))}</strong>
          <small>Document metadata entries.</small>
        </article>
        <article>
          <span>Compliance</span>
          <strong>${escapeHtml(String(summary.compliance.length))}</strong>
          <small>Compliance areas tracked.</small>
        </article>
      </div>
      ${renderCaClientMaster()}
      <div class="planned-org-module-grid" style="margin-top:1rem">
        ${clients.map((row) => `
          <article>
            <div>
              <h4>${escapeHtml(row.client)}</h4>
              <button class="secondary" type="button" data-business-action="ca-client-filter" data-client-name="${escapeHtml(row.client)}">Switch</button>
            </div>
            <p>${escapeHtml(String(row.count || 0))} document(s) in the current client queue.${caPracticeFilters.client_name === row.client ? " Active company filter." : ""}</p>
            ${row.owner || row.compliance ? `<span class="row-subtext">${escapeHtml([row.owner, row.compliance].filter(Boolean).join(" · "))}</span>` : ""}
          </article>
        `).join("")}
      </div>
      ${caPracticeFilters.client_name ? `
      <div class="settings-boundary-note" style="margin-top:1rem">
        <strong>Company switch:</strong>
        Viewing CA queue for <strong>${escapeHtml(caPracticeFilters.client_name)}</strong>.
        <button class="secondary" type="button" data-business-action="ca-client-filter-clear" style="margin-left:.5rem">Clear</button>
      </div>` : ""}
      ${renderCaDocumentIntake(model.documentIntake)}
    </div>
  `;
}

function renderProfessionalSuiteWorkspace() {
  const model = plannedOrgWorkspaceModel("PROFESSIONAL");
  const cards = [
    ["Client Billing", "Create GST-ready service invoices in the active Sales workspace.", "sales", "Open Sales"],
    ["Client Accounts", "Maintain professional clients and vendors in Parties.", "parties", "Open Parties"],
    ["Receipts", "Record client receipts and journal entries through the voucher workflow.", "vouchers", "Open Vouchers"],
    ["Professional Reports", "Review ledger-backed financial statements and receivables.", "reports", "Open Reports"],
  ];
  return `
    <div class="verification-panel erp-workspace-panel professional-suite-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">${escapeHtml(model.eyebrow)}</span>
          <h4>Professional Suite</h4>
          <p>${escapeHtml(model.lead)}</p>
        </div>
        <span class="pill ok">MitraBooks workflow active</span>
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
        ${cards.map(([title, copy, workspace, action]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(workspace)}">${escapeHtml(action)}</button>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>
        `).join("")}
      </div>
      <div class="settings-boundary-note">
        <strong>Current state:</strong>
        Professional Suite uses the active MitraBooks tenant for billing, parties, receipts, and reports. Deferred scope: retainer-specific automation and separate professional-only tenant context.
      </div>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS WORKSPACE DISPATCHER
// NOTE  : renderBusinessWorkspace — top-level if/else dispatches to each workspace render function
// ══════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════
// MANUFACTURING & COST-CENTRE ADD-ON (enterprise, opt-in)
// Backend /api/v1/business/mfg/*. Menu always shows; content gates on
// GET /business/mfg/access (platform provisioning + tenant enable + role).
// Two independent layers: Cost-Centre Accounting and Manufacturing.
// ══════════════════════════════════════════════════════════════════════

let mfgAccess = null;            // GET /business/mfg/access
let mfgTab = "cost-centres";     // cost-centres | budgets | pl | boms | work-orders
let mfgError = "";
let mfgCostCentres = [];         // from /business/dimensions (cost_centres)
let mfgTree = [];                // hierarchy roots
let mfgBudgets = [];
let mfgBudgetVsActual = null;    // {budget_id, report}
let mfgBoms = [];
let mfgWorkOrders = [];
let mfgItems = [];               // inventory items for selects
let mfgPl = null;                // cost-centre P&L report
let mfgPlFrom = "";
let mfgPlTo = "";
let mfgBomDraft = [];            // [{item_id, qty, rate, scrap_pct}] while building a BOM
let mfgWoActualDraft = [];       // [{item_id, qty, rate}] while completing a work order
let mfgCompleteFor = "";         // wo_id being completed

function mfgMoney(value) {
  const n = Number(value || 0);
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function mfgCanManage() {
  return !!(mfgAccess && mfgAccess.can_manage_cost_centre);
}

function mfgCanManageMfg() {
  return !!(mfgAccess && mfgAccess.can_manage_manufacturing);
}

function refreshMfgView() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "manufacturing") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadMfgWorkspace() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/access", { method: "GET" });
  mfgAccess = res.ok ? res.payload : { cost_centre_active: false, cost_centre_available: false, error: res.payload?.detail };
  refreshMfgView();
  if (mfgAccess && mfgAccess.cost_centre_active) {
    loadMfgCostCentres();
    loadMfgTree();
    loadMfgBudgets();
    loadMfgItems();
    if (mfgAccess.manufacturing_active) {
      loadMfgBoms();
      loadMfgWorkOrders();
    }
  }
}

async function loadMfgCostCentres() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/dimensions", { method: "GET" });
  mfgCostCentres = res.ok && Array.isArray(res.payload?.cost_centres) ? res.payload.cost_centres : [];
  refreshMfgView();
}

async function loadMfgTree() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/tree", { method: "GET" });
  mfgTree = res.ok && Array.isArray(res.payload?.roots) ? res.payload.roots : [];
  refreshMfgView();
}

async function loadMfgBudgets() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/budgets", { method: "GET" });
  mfgBudgets = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

async function loadMfgItems() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", { method: "GET" });
  mfgItems = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

async function loadMfgBoms() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/boms", { method: "GET" });
  mfgBoms = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

async function loadMfgWorkOrders() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/work-orders", { method: "GET" });
  mfgWorkOrders = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

async function loadMfgPl() {
  const qs = [];
  if (mfgPlFrom) qs.push("from_date=" + encodeURIComponent(mfgPlFrom));
  if (mfgPlTo) qs.push("to_date=" + encodeURIComponent(mfgPlTo));
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/pl" + (qs.length ? "?" + qs.join("&") : ""), { method: "GET" });
  mfgPl = res.ok ? res.payload : null;
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not load cost-centre P&L.");
  refreshMfgView();
}

// ---- enable toggles ----
async function mfgEnableLayer(layer) {
  const path = layer === "manufacturing" ? "/manufacturing/enabled" : "/cost-centre/enabled";
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg" + path, {
    method: "PUT", body: JSON.stringify({ enabled: true }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not enable the module.");
  loadMfgWorkspace();
}

// ---- cost centres ----
async function mfgCreateCostCentre() {
  const code = (document.getElementById("mfg-cc-code")?.value || "").trim();
  const name = (document.getElementById("mfg-cc-name")?.value || "").trim();
  const parent = (document.getElementById("mfg-cc-parent")?.value || "").trim();
  if (!name) { mfgError = "Cost centre needs a name."; refreshMfgView(); return; }
  const body = { dimension_type: "cost_centre", code, name };
  if (parent) body.parent_code = parent;
  const res = await apiRequest("mitrabooks", "/api/v1/business/dimensions", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create cost centre.");
  await loadMfgCostCentres();
  await loadMfgTree();
}

// ---- budgets ----
async function mfgCreateBudget() {
  const ccId = document.getElementById("mfg-bud-cc")?.value || "";
  const year = parseInt(document.getElementById("mfg-bud-year")?.value, 10);
  const monthRaw = document.getElementById("mfg-bud-month")?.value || "";
  const accountId = parseInt(document.getElementById("mfg-bud-account")?.value, 10);
  const amount = document.getElementById("mfg-bud-amount")?.value || "";
  if (!ccId || !year || !accountId || !amount) { mfgError = "Pick cost centre, year, account and amount."; refreshMfgView(); return; }
  const body = {
    cost_centre_id: ccId, fiscal_year: year,
    fiscal_month: monthRaw ? parseInt(monthRaw, 10) : null,
    lines: [{ account_id: accountId, allocated_amount: amount }],
  };
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/budgets", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create budget.");
  await loadMfgBudgets();
}

async function mfgSetBudgetStatus(button) {
  const id = button.getAttribute("data-budget-id") || "";
  const status = button.getAttribute("data-status") || "";
  if (!id || !status) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/cost-centre/budgets/${encodeURIComponent(id)}/status`, {
    method: "PUT", body: JSON.stringify({ status }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not update budget status.");
  await loadMfgBudgets();
}

async function mfgViewBudgetVsActual(button) {
  const id = button.getAttribute("data-budget-id") || "";
  if (!id) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/cost-centre/budgets/${encodeURIComponent(id)}/vs-actual`, { method: "GET" });
  mfgBudgetVsActual = res.ok ? res.payload : null;
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not load budget vs actual.");
  refreshMfgView();
}

// ---- BOMs ----
function mfgAddBomComponent() {
  const itemId = document.getElementById("mfg-bom-comp-item")?.value || "";
  const qty = document.getElementById("mfg-bom-comp-qty")?.value || "";
  const rate = document.getElementById("mfg-bom-comp-rate")?.value || "";
  const scrap = document.getElementById("mfg-bom-comp-scrap")?.value || "0";
  if (!itemId || !qty) { mfgError = "Component needs an item and quantity."; refreshMfgView(); return; }
  mfgBomDraft.push({ item_id: itemId, qty, rate: rate || "0", scrap_pct: scrap || "0" });
  mfgError = "";
  refreshMfgView();
}

function mfgRemoveBomComponent(button) {
  const idx = parseInt(button.getAttribute("data-idx"), 10);
  if (!isNaN(idx)) mfgBomDraft.splice(idx, 1);
  refreshMfgView();
}

async function mfgCreateBom() {
  const fgItemId = document.getElementById("mfg-bom-fg")?.value || "";
  const code = (document.getElementById("mfg-bom-code")?.value || "").trim();
  const outputQty = document.getElementById("mfg-bom-output")?.value || "1";
  if (!fgItemId) { mfgError = "Pick a finished good."; refreshMfgView(); return; }
  if (!mfgBomDraft.length) { mfgError = "Add at least one component."; refreshMfgView(); return; }
  const body = { fg_item_id: fgItemId, output_qty: outputQty, components: mfgBomDraft };
  if (code) body.code = code;
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/boms", {
    method: "POST", body: JSON.stringify(body),
  });
  if (res.ok) { mfgBomDraft = []; mfgError = ""; }
  else { mfgError = res.payload?.detail || "Could not create BOM."; }
  await loadMfgBoms();
}

// ---- work orders ----
async function mfgCreateWorkOrder() {
  const bomId = document.getElementById("mfg-wo-bom")?.value || "";
  const qty = document.getElementById("mfg-wo-qty")?.value || "";
  const ccId = document.getElementById("mfg-wo-cc")?.value || "";
  if (!bomId || !qty) { mfgError = "Pick a BOM and planned quantity."; refreshMfgView(); return; }
  const body = { bom_id: bomId, planned_qty: qty };
  if (ccId) body.cost_centre_id = ccId;
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/work-orders", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create work order.");
  await loadMfgWorkOrders();
}

async function mfgSetWorkOrderStatus(button) {
  const id = button.getAttribute("data-wo-id") || "";
  const status = button.getAttribute("data-status") || "";
  if (!id || !status) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/work-orders/${encodeURIComponent(id)}/status`, {
    method: "PUT", body: JSON.stringify({ status }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not update work order.");
  await loadMfgWorkOrders();
}

function mfgOpenComplete(button) {
  mfgCompleteFor = button.getAttribute("data-wo-id") || "";
  mfgWoActualDraft = [];
  mfgError = "";
  refreshMfgView();
}

function mfgAddWoActual() {
  const itemId = document.getElementById("mfg-wo-act-item")?.value || "";
  const qty = document.getElementById("mfg-wo-act-qty")?.value || "";
  const rate = document.getElementById("mfg-wo-act-rate")?.value || "0";
  if (!itemId || !qty) { mfgError = "Actual line needs an item and quantity."; refreshMfgView(); return; }
  mfgWoActualDraft.push({ item_id: itemId, qty, rate: rate || "0" });
  mfgError = "";
  refreshMfgView();
}

function mfgRemoveWoActual(button) {
  const idx = parseInt(button.getAttribute("data-idx"), 10);
  if (!isNaN(idx)) mfgWoActualDraft.splice(idx, 1);
  refreshMfgView();
}

async function mfgCompleteWorkOrder() {
  const produced = document.getElementById("mfg-wo-produced")?.value || "";
  const overhead = document.getElementById("mfg-wo-overhead")?.value || "0";
  if (!mfgCompleteFor) return;
  if (!produced) { mfgError = "Enter produced quantity."; refreshMfgView(); return; }
  if (!mfgWoActualDraft.length) { mfgError = "Add actual material consumption."; refreshMfgView(); return; }
  const body = { produced_qty: produced, actual_overhead: overhead, actual_components: mfgWoActualDraft };
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/work-orders/${encodeURIComponent(mfgCompleteFor)}/complete`, {
    method: "POST", body: JSON.stringify(body),
  });
  if (res.ok) { mfgCompleteFor = ""; mfgWoActualDraft = []; mfgError = ""; }
  else { mfgError = res.payload?.detail || "Could not complete work order."; }
  await loadMfgWorkOrders();
}

function mfgItemName(itemId) {
  const it = mfgItems.find((i) => i.item_id === itemId);
  return it ? `${it.code} — ${it.name}` : itemId;
}

function mfgItemOptions(selectedId) {
  return mfgItems.map((i) =>
    `<option value="${escapeHtml(i.item_id)}"${i.item_id === selectedId ? " selected" : ""}>${escapeHtml(i.code)} — ${escapeHtml(i.name)}</option>`
  ).join("");
}

function mfgTabButton(key, label) {
  const active = mfgTab === key ? " active" : "";
  return `<button type="button" class="erp-tab${active}" data-business-action="mfg-tab" data-mfg-tab="${key}">${escapeHtml(label)}</button>`;
}

// ---- tab renderers ----
function mfgRenderTreeNodes(nodes, depth) {
  return nodes.map((n) => `
    <div style="padding:4px 0 4px ${depth * 18}px;">
      <strong>${escapeHtml(n.code)}</strong> — ${escapeHtml(n.name)}${n.is_active === false ? ' <span class="muted">(inactive)</span>' : ""}
    </div>
    ${n.children && n.children.length ? mfgRenderTreeNodes(n.children, depth + 1) : ""}
  `).join("");
}

function renderMfgCostCentresTab() {
  const createForm = mfgCanManage() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>Code<input id="mfg-cc-code" placeholder="MFG-ASY-01" /></label>
      <label>Name<input id="mfg-cc-name" placeholder="Assembly Line 1" /></label>
      <label>Parent code<input id="mfg-cc-parent" placeholder="(optional)" /></label>
      <button class="primary" type="button" data-business-action="mfg-create-cc">+ Add Cost Centre</button>
    </div>` : "";
  const rows = mfgCostCentres.length
    ? mfgCostCentres.map((c) => `<tr><td>${escapeHtml(c.code)}</td><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.parent_code || "—")}</td><td>${c.is_active === false ? "Inactive" : "Active"}</td></tr>`).join("")
    : `<tr><td colspan="4" class="muted">No cost centres yet.</td></tr>`;
  const tree = mfgTree.length ? `
    <h5 style="margin-top:16px;">Hierarchy</h5>
    <div class="erp-tree">${mfgRenderTreeNodes(mfgTree, 0)}</div>` : "";
  return `
    ${createForm}
    <table class="erp-table"><thead><tr><th>Code</th><th>Name</th><th>Parent</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
    ${tree}`;
}

function renderMfgBudgetsTab() {
  const ccOptions = mfgCostCentres.map((c) => `<option value="${escapeHtml(c.dimension_id)}">${escapeHtml(c.code)} — ${escapeHtml(c.name)}</option>`).join("");
  const acctOptions = (lastBusinessAccounts || []).map((a) => `<option value="${escapeHtml(a.id || a.account_id)}">${escapeHtml(a.code)} — ${escapeHtml(a.name)}</option>`).join("");
  const createForm = mfgCanManage() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>Cost centre<select id="mfg-bud-cc">${ccOptions}</select></label>
      <label>Year<input id="mfg-bud-year" type="number" value="${new Date().getFullYear()}" style="width:90px;" /></label>
      <label>Month<select id="mfg-bud-month"><option value="">Annual</option>${[1,2,3,4,5,6,7,8,9,10,11,12].map((m) => `<option value="${m}">${m}</option>`).join("")}</select></label>
      <label>Account<select id="mfg-bud-account">${acctOptions}</select></label>
      <label>Amount<input id="mfg-bud-amount" type="number" placeholder="0.00" /></label>
      <button class="primary" type="button" data-business-action="mfg-create-budget">+ Add Budget</button>
    </div>` : "";
  const ccName = (id) => { const c = mfgCostCentres.find((x) => x.dimension_id === id); return c ? c.code : id; };
  const rows = mfgBudgets.length
    ? mfgBudgets.map((b) => {
        const actions = mfgCanManage()
          ? `${b.status === "DRAFT" ? `<button class="secondary" type="button" data-business-action="mfg-budget-status" data-budget-id="${escapeHtml(b.budget_id)}" data-status="APPROVED">Approve</button>` : ""}
             ${b.status === "APPROVED" ? `<button class="secondary" type="button" data-business-action="mfg-budget-status" data-budget-id="${escapeHtml(b.budget_id)}" data-status="LOCKED">Lock</button>` : ""}`
          : "";
        return `<tr>
          <td>${escapeHtml(ccName(b.cost_centre_id))}</td>
          <td>${escapeHtml(b.fiscal_year)}${b.fiscal_month ? "-" + escapeHtml(b.fiscal_month) : " (annual)"}</td>
          <td>${escapeHtml(b.status)}</td>
          <td>${(b.lines || []).length} line(s)</td>
          <td><button class="secondary" type="button" data-business-action="mfg-budget-vs-actual" data-budget-id="${escapeHtml(b.budget_id)}">Vs Actual</button> ${actions}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="5" class="muted">No budgets yet.</td></tr>`;
  let vsActual = "";
  if (mfgBudgetVsActual) {
    const r = mfgBudgetVsActual;
    const vrows = (r.rows || []).map((x) => `<tr><td>${escapeHtml(x.code || "")}</td><td>${escapeHtml(x.name || "")}</td><td style="text-align:right;">${mfgMoney(x.allocated)}</td><td style="text-align:right;">${mfgMoney(x.actual)}</td><td style="text-align:right;">${mfgMoney(x.variance)}</td><td style="text-align:right;">${escapeHtml(x.burn_rate_pct)}%</td></tr>`).join("");
    vsActual = `
      <h5 style="margin-top:16px;">Budget vs Actual</h5>
      <table class="erp-table"><thead><tr><th>Account</th><th>Name</th><th style="text-align:right;">Allocated</th><th style="text-align:right;">Actual</th><th style="text-align:right;">Variance</th><th style="text-align:right;">Burn</th></tr></thead>
      <tbody>${vrows || `<tr><td colspan="6" class="muted">No data.</td></tr>`}</tbody>
      <tfoot><tr><td colspan="2"><strong>Total</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.allocated)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.actual)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.variance)}</strong></td><td></td></tr></tfoot></table>`;
  }
  return `${createForm}
    <table class="erp-table"><thead><tr><th>Cost centre</th><th>Period</th><th>Status</th><th>Lines</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>
    ${vsActual}`;
}

function renderMfgPlTab() {
  const controls = `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>From<input id="mfg-pl-from" type="date" value="${escapeHtml(mfgPlFrom)}" /></label>
      <label>To<input id="mfg-pl-to" type="date" value="${escapeHtml(mfgPlTo)}" /></label>
      <button class="primary" type="button" data-business-action="mfg-pl-run">Run</button>
      <button class="secondary" type="button" data-business-action="mfg-pl-export" data-format="csv">Export CSV</button>
      <button class="secondary" type="button" data-business-action="mfg-pl-export" data-format="xlsx">Export Excel</button>
    </div>`;
  if (!mfgPl) return controls + `<p class="muted">Run the report to see cost-centre P&amp;L.</p>`;
  const rows = (mfgPl.rows || []).map((x) => `<tr><td>${escapeHtml(x.code)}</td><td>${escapeHtml(x.name)}</td><td style="text-align:right;">${mfgMoney(x.income)}</td><td style="text-align:right;">${mfgMoney(x.expense)}</td><td style="text-align:right;">${mfgMoney(x.net)}</td></tr>`).join("");
  const u = mfgPl.untagged || {};
  const t = mfgPl.totals || {};
  return controls + `
    <table class="erp-table"><thead><tr><th>Code</th><th>Cost centre</th><th style="text-align:right;">Income</th><th style="text-align:right;">Expense</th><th style="text-align:right;">Net</th></tr></thead>
    <tbody>${rows || `<tr><td colspan="5" class="muted">No tagged activity in this period.</td></tr>`}
    <tr><td></td><td>Untagged</td><td style="text-align:right;">${mfgMoney(u.income)}</td><td style="text-align:right;">${mfgMoney(u.expense)}</td><td style="text-align:right;">${mfgMoney(u.net)}</td></tr></tbody>
    <tfoot><tr><td colspan="2"><strong>Total</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.income)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.expense)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.net)}</strong></td></tr></tfoot></table>`;
}

function renderMfgBomsTab() {
  if (!mfgAccess || !mfgAccess.manufacturing_active) {
    return `<div class="module-state warn"><strong>Manufacturing layer is off</strong><span>Enable Manufacturing (it builds on Cost Centres) to define BOMs and work orders.</span></div>
      ${mfgAccess && mfgAccess.can_enable_manufacturing ? `<button class="primary" type="button" data-business-action="mfg-enable-manufacturing" style="margin-top:10px;">Enable Manufacturing</button>` : ""}`;
  }
  const draftRows = mfgBomDraft.map((c, i) => `<tr><td>${escapeHtml(mfgItemName(c.item_id))}</td><td>${escapeHtml(c.qty)}</td><td>${escapeHtml(c.rate)}</td><td>${escapeHtml(c.scrap_pct)}%</td><td><button class="secondary" type="button" data-business-action="mfg-bom-remove-comp" data-idx="${i}">✕</button></td></tr>`).join("");
  const createForm = mfgCanManageMfg() ? `
    <details style="margin-bottom:14px;"><summary><strong>+ New BOM</strong></summary>
      <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:10px 0;">
        <label>Finished good<select id="mfg-bom-fg">${mfgItemOptions("")}</select></label>
        <label>Code<input id="mfg-bom-code" placeholder="(auto)" /></label>
        <label>Output qty<input id="mfg-bom-output" type="number" value="1" style="width:90px;" /></label>
      </div>
      <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
        <label>Component<select id="mfg-bom-comp-item">${mfgItemOptions("")}</select></label>
        <label>Qty<input id="mfg-bom-comp-qty" type="number" style="width:80px;" /></label>
        <label>Rate<input id="mfg-bom-comp-rate" type="number" style="width:90px;" /></label>
        <label>Scrap %<input id="mfg-bom-comp-scrap" type="number" value="0" style="width:70px;" /></label>
        <button class="secondary" type="button" data-business-action="mfg-bom-add-comp">Add line</button>
      </div>
      <table class="erp-table" style="margin-top:10px;"><thead><tr><th>Component</th><th>Qty</th><th>Rate</th><th>Scrap</th><th></th></tr></thead><tbody>${draftRows || `<tr><td colspan="5" class="muted">No components added.</td></tr>`}</tbody></table>
      <button class="primary" type="button" data-business-action="mfg-create-bom" style="margin-top:10px;">Save BOM</button>
    </details>` : "";
  const rows = mfgBoms.length
    ? mfgBoms.map((b) => `<tr><td>${escapeHtml(b.code)}</td><td>${escapeHtml(b.fg_item_name || b.fg_item_code || "")}</td><td>${escapeHtml(b.output_qty)}</td><td style="text-align:right;">${mfgMoney(b.standard_cost?.total_cost)}</td><td style="text-align:right;">${mfgMoney(b.standard_cost?.per_unit_cost)}</td></tr>`).join("")
    : `<tr><td colspan="5" class="muted">No BOMs yet.</td></tr>`;
  return `${createForm}
    <table class="erp-table"><thead><tr><th>BOM</th><th>Finished good</th><th>Output</th><th style="text-align:right;">Std cost</th><th style="text-align:right;">Per unit</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderMfgWorkOrdersTab() {
  if (!mfgAccess || !mfgAccess.manufacturing_active) {
    return `<div class="module-state warn"><strong>Manufacturing layer is off</strong><span>Enable Manufacturing to track work orders.</span></div>`;
  }
  const bomOptions = mfgBoms.map((b) => `<option value="${escapeHtml(b.bom_id)}">${escapeHtml(b.code)} — ${escapeHtml(b.fg_item_name || b.fg_item_code || "")}</option>`).join("");
  const ccOptions = `<option value="">(no cost centre)</option>` + mfgCostCentres.map((c) => `<option value="${escapeHtml(c.dimension_id)}">${escapeHtml(c.code)}</option>`).join("");
  const createForm = mfgCanManageMfg() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>BOM<select id="mfg-wo-bom">${bomOptions}</select></label>
      <label>Planned qty<input id="mfg-wo-qty" type="number" style="width:100px;" /></label>
      <label>Cost centre<select id="mfg-wo-cc">${ccOptions}</select></label>
      <button class="primary" type="button" data-business-action="mfg-create-wo">+ Create Work Order</button>
    </div>` : "";
  const statusBtn = (wo, status, label) => `<button class="secondary" type="button" data-business-action="mfg-wo-status" data-wo-id="${escapeHtml(wo.wo_id)}" data-status="${status}">${label}</button>`;
  const rows = mfgWorkOrders.length
    ? mfgWorkOrders.map((wo) => {
        let actions = "";
        if (mfgCanManageMfg()) {
          if (wo.status === "draft") actions = statusBtn(wo, "released", "Release") + " " + statusBtn(wo, "cancelled", "Cancel");
          else if (wo.status === "released") actions = statusBtn(wo, "in_progress", "Start") + " " + `<button class="primary" type="button" data-business-action="mfg-wo-open-complete" data-wo-id="${escapeHtml(wo.wo_id)}">Complete</button>`;
          else if (wo.status === "in_progress") actions = `<button class="primary" type="button" data-business-action="mfg-wo-open-complete" data-wo-id="${escapeHtml(wo.wo_id)}">Complete</button>`;
        }
        const variance = wo.variance ? mfgMoney(wo.variance.variance) + (wo.variance.favourable ? " ✓" : "") : "—";
        return `<tr><td>${escapeHtml(wo.wo_number)}</td><td>${escapeHtml(wo.fg_item_name || wo.fg_item_code || "")}</td><td>${escapeHtml(wo.planned_qty)}</td><td>${escapeHtml(wo.status)}</td><td style="text-align:right;">${mfgMoney(wo.standard_cost?.total_cost)}</td><td style="text-align:right;">${variance}</td><td>${actions}</td></tr>`;
      }).join("")
    : `<tr><td colspan="7" class="muted">No work orders yet.</td></tr>`;
  let completeForm = "";
  if (mfgCompleteFor) {
    const draftRows = mfgWoActualDraft.map((c, i) => `<tr><td>${escapeHtml(mfgItemName(c.item_id))}</td><td>${escapeHtml(c.qty)}</td><td>${escapeHtml(c.rate)}</td><td><button class="secondary" type="button" data-business-action="mfg-wo-remove-actual" data-idx="${i}">✕</button></td></tr>`).join("");
    completeForm = `
      <div class="verification-panel" style="margin-top:14px;padding:14px;">
        <h5>Complete work order — actual consumption</h5>
        <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
          <label>Produced qty<input id="mfg-wo-produced" type="number" style="width:100px;" /></label>
          <label>Actual overhead<input id="mfg-wo-overhead" type="number" value="0" style="width:110px;" /></label>
        </div>
        <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-top:8px;">
          <label>Material<select id="mfg-wo-act-item">${mfgItemOptions("")}</select></label>
          <label>Qty<input id="mfg-wo-act-qty" type="number" style="width:80px;" /></label>
          <label>Rate<input id="mfg-wo-act-rate" type="number" style="width:90px;" /></label>
          <button class="secondary" type="button" data-business-action="mfg-wo-add-actual">Add line</button>
        </div>
        <table class="erp-table" style="margin-top:8px;"><thead><tr><th>Material</th><th>Qty</th><th>Rate</th><th></th></tr></thead><tbody>${draftRows || `<tr><td colspan="4" class="muted">No actuals added.</td></tr>`}</tbody></table>
        <button class="primary" type="button" data-business-action="mfg-wo-complete" style="margin-top:10px;">Confirm Completion</button>
        <button class="secondary" type="button" data-business-action="mfg-wo-complete-cancel" style="margin-top:10px;">Cancel</button>
      </div>`;
  }
  return `${createForm}
    <table class="erp-table"><thead><tr><th>WO</th><th>Finished good</th><th>Qty</th><th>Status</th><th style="text-align:right;">Std cost</th><th style="text-align:right;">Variance</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>
    ${completeForm}`;
}

function renderMfgTab() {
  if (mfgTab === "budgets") return renderMfgBudgetsTab();
  if (mfgTab === "pl") return renderMfgPlTab();
  if (mfgTab === "boms") return renderMfgBomsTab();
  if (mfgTab === "work-orders") return renderMfgWorkOrdersTab();
  return renderMfgCostCentresTab();
}

function renderManufacturingWorkspace() {
  let body;
  if (!mfgAccess) {
    body = `<p class="muted">Loading manufacturing workspace…</p>`;
  } else if (!mfgAccess.cost_centre_active) {
    if (mfgAccess.cost_centre_available === false) {
      body = `<div class="module-state warn"><strong>Manufacturing &amp; Cost Centres is not active</strong><span>This enterprise add-on has not been provisioned for your organization. Contact your platform administrator to enable it.</span></div>`;
    } else if (mfgAccess.can_enable_cost_centre) {
      body = `
        <div class="module-state warn">
          <strong>Cost-Centre Accounting is provisioned but turned off</strong>
          <span>Enable it to tag postings to cost centres and run departmental P&amp;L and budgets.</span>
        </div>
        <button class="primary" type="button" data-business-action="mfg-enable-cost-centre" style="margin-top:10px;">Enable Cost Centres</button>`;
    } else {
      body = `<div class="module-state warn"><strong>Manufacturing &amp; Cost Centres is turned off</strong><span>Ask an administrator to enable it in MitraBooks.</span></div>`;
    }
  } else {
    body = `
      ${mfgError ? `<div class="module-state danger"><span>${escapeHtml(mfgError)}</span></div>` : ""}
      <div class="erp-tabs" style="display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;">
        ${mfgTabButton("cost-centres", "Cost Centres")}
        ${mfgTabButton("budgets", "Budgets")}
        ${mfgTabButton("pl", "Cost-Centre P&L")}
        ${mfgTabButton("boms", "BOMs")}
        ${mfgTabButton("work-orders", "Work Orders")}
      </div>
      <div class="erp-tab-content">${renderMfgTab()}</div>`;
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div><h4>Manufacturing &amp; Cost Centres</h4><p>Cost-centre accounting, budgets, BOMs and work orders.</p></div>
        <button class="secondary" type="button" data-business-action="mfg-refresh">Refresh</button>
      </div>
      ${body}
    </div>`;
}

function renderBusinessWorkspace() {
  if (activeBusinessWorkspace === "settings") {
    return renderMitraBooksSettingsWorkspace();
  }
  if (activeBusinessWorkspace === "ca-access") {
    return renderCaPracticePortalWorkspace();
  }
  if (activeBusinessWorkspace === "parties") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Parties</h4>
            <p>Customers and vendors for this business workspace.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-party">+ New Party</button>
        </div>
        ${renderBusinessPartiesListFilters(lastBusinessParties.length)}
        ${renderBusinessPartiesTable(lastBusinessParties)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "vouchers") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Vouchers</h4>
            <p>Posted journal entries, payments, receipts, and contra vouchers.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-voucher" aria-keyshortcuts="Control+Alt+V">+ New Voucher</button>
        </div>
        ${renderVoucherApprovalQueuePanel(lastVoucherApprovalQueue)}
        ${renderBusinessVouchersListFilters(lastBusinessVouchers.length)}
        ${renderBusinessVouchersTable(lastBusinessVouchers)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "audit") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Audit Trail</h4>
            <p>All party, voucher, and account changes for compliance and troubleshooting.</p>
          </div>
        </div>
        ${renderAuditListFilters(lastAuditEvents.length)}
        ${renderAuditEventsTable(lastAuditEvents)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "accounting") {
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
  if (activeBusinessWorkspace === "reports"
      || activeBusinessWorkspace === "gst-returns"
      || activeBusinessWorkspace === "reconciliation"
      || activeBusinessWorkspace === "tds-tcs"
      || activeBusinessWorkspace === "bank-recon") {
    return renderBusinessReportsWorkspace();
  }
  if (activeBusinessWorkspace === "sales") {
    return renderBusinessSalesWorkspace();
  }
  if (activeBusinessWorkspace === "bills") {
    return renderBusinessPurchaseWorkspace();
  }
  if (activeBusinessWorkspace === "credit-notes") {
    return renderBusinessCreditNoteWorkspace();
  }
  if (activeBusinessWorkspace === "debit-notes") {
    return renderBusinessDebitNoteWorkspace();
  }
  if (activeBusinessWorkspace === "coa") {
    return renderBusinessCoaWorkspace();
  }
  if (activeBusinessWorkspace === "financial-health") {
    return renderFinancialHealthWorkspace();
  }
  if (activeBusinessWorkspace === "hr") {
    return renderHrWorkspace();
  }
  if (activeBusinessWorkspace === "manufacturing") {
    return renderManufacturingWorkspace();
  }
  return `
    <div class="erp-workbench-grid">
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Core Master</span>
        <h4>Parties</h4>
        <strong>${escapeHtml(lastBusinessParties.length)}</strong>
        <p>Customers and vendors available for business posting.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="parties">Open Parties</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Posting</span>
        <h4>Vouchers</h4>
        <strong>${escapeHtml(lastBusinessVouchers.length)}</strong>
        <p>Posted journal entries, receipts, payments, and reversals.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">Open Vouchers</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Chart</span>
        <h4>Accounts</h4>
        <strong>${escapeHtml(lastBusinessAccounts.length)}</strong>
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

// Financial Health (CFO Insight) — every figure is computed server-side from the
// posted ledger (see app/modules/business/financial_health.py). The frontend only
// renders the trusted KPI/chart/alert payload; it never derives figures itself.

function fhKpiDisplay(kpi) {
  const unit = kpi.unit || "";
  const value = kpi.value;
  if (value === "—" || value === null || value === undefined || value === "") return "—";
  if (unit === "₹") return formatCurrency(value);
  if (unit === "%") return `${value}%`;
  if (unit === "x") return `${value}×`;
  return `${value}${unit ? " " + unit : ""}`;
}

function renderFhKpiCard(kpi) {
  return `
    <article class="fh-kpi fh-tone-${escapeHtml(kpi.tone || "neutral")}">
      <span class="fh-kpi-label">${escapeHtml(kpi.label)}</span>
      <strong class="fh-kpi-value">${escapeHtml(fhKpiDisplay(kpi))}</strong>
      <small class="fh-kpi-hint">${escapeHtml(kpi.hint || "")}</small>
    </article>
  `;
}

function renderFhBarChart(chart) {
  const series = Array.isArray(chart.series) ? chart.series : [];
  const labels = Array.isArray(chart.x) ? chart.x : [];
  const all = series.flatMap((s) => (s.data || []).map((v) => Math.abs(Number(v) || 0)));
  const maxValue = all.length ? Math.max(...all, 0.0001) : 1;
  const seriesClass = ["fh-bar-a", "fh-bar-b"];

  const groups = labels.map((label, i) => {
    const bars = series.map((s, si) => {
      const raw = Number((s.data || [])[i]) || 0;
      const height = Math.max(3, Math.round((Math.abs(raw) / maxValue) * 120));
      const neg = raw < 0 ? " fh-bar-neg" : "";
      return `<span class="fh-bar ${seriesClass[si] || "fh-bar-a"}${neg}" style="height:${height}px" title="${escapeHtml(s.name)}: ${escapeHtml(raw)}"></span>`;
    }).join("");
    return `
      <div class="fh-bar-group">
        <div class="fh-bars">${bars}</div>
        <small>${escapeHtml(label)}</small>
      </div>`;
  }).join("");

  const legend = series.length > 1
    ? `<div class="fh-legend">${series.map((s, si) =>
        `<span><i class="fh-dot ${seriesClass[si] || "fh-bar-a"}"></i>${escapeHtml(s.name)}</span>`).join("")}</div>`
    : "";

  return `
    <article class="fh-chart-card">
      <div class="fh-chart-head"><h5>${escapeHtml(chart.title)}</h5><span class="fh-unit">${escapeHtml(chart.unit || "")}</span></div>
      <div class="fh-chart" role="img" aria-label="${escapeHtml(chart.title)}">${groups || '<p class="muted">No data.</p>'}</div>
      ${legend}
    </article>`;
}

function renderFhAlert(alert) {
  return `
    <li class="fh-alert fh-alert-${escapeHtml(alert.severity || "info")}">
      <strong>${escapeHtml(alert.title || "")}</strong>
      <span>${escapeHtml(alert.message || "")}</span>
    </li>`;
}

// Render the model's plain-text narrative safely: escape everything, then turn
// blank-line-separated blocks into paragraphs and "-"/"•" lines into list items.
function fhFormatNarrative(text) {
  const lines = String(text || "").split(/\r?\n/);
  const out = [];
  let listItems = [];
  const flushList = () => {
    if (listItems.length) { out.push(`<ul>${listItems.join("")}</ul>`); listItems = []; }
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); continue; }
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    if (bullet) {
      listItems.push(`<li>${escapeHtml(bullet[1])}</li>`);
    } else {
      flushList();
      out.push(`<p>${escapeHtml(line)}</p>`);
    }
  }
  flushList();
  return out.join("");
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: CHART OF ACCOUNTS (COA) WORKSPACE
// API   : GET /api/v1/accounting/accounts  POST .../accounts  PATCH .../accounts/{code}
// NOTE  : renderBusinessCoaWorkspace — name-edit only, codes are permanent, type filter dropdown
// ══════════════════════════════════════════════════════════════════════


// ── Chart of Accounts workspace ─────────────────────────────────────────────

const COA_TYPE_META = {
  asset:     { label: "Asset",     pillClass: "pill ok" },
  liability: { label: "Liability", pillClass: "pill danger" },
  equity:    { label: "Equity",    pillClass: "pill neutral" },
  income:    { label: "Income",    pillClass: "pill ok" },
  expense:   { label: "Expense",   pillClass: "pill warn" },
};
const COA_CLASS_LABELS = {
  personal: "Personal", real: "Real", nominal: "Nominal",
};

function coaTypePill(type) {
  const m = COA_TYPE_META[type] || { label: (type || "—"), pillClass: "pill" };
  return `<span class="${m.pillClass}">${m.label}</span>`;
}

function renderBusinessCoaWorkspace() {
  const accounts = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [];
  const filtered = coaTypeFilter ? accounts.filter((a) => a.type === coaTypeFilter) : accounts;

  const typeOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}">${m.label}</option>`).join("");
  const classOptions = Object.entries(COA_CLASS_LABELS)
    .map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  const filterOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}" ${coaTypeFilter === v ? "selected" : ""}>${m.label}</option>`).join("");

  const rows = filtered.length === 0
    ? `<tr><td colspan="6" class="empty-state-cell" style="text-align:center;padding:1.5rem">No accounts match the selected filter.</td></tr>`
    : filtered.map((a) => {
        const isSystem = a.is_cash_bank || a.is_receivable || a.is_payable;
        const systemBadge = isSystem ? `<span class="pill neutral" style="font-size:.72rem">System</span>` : "";
        return `
          <tr data-coa-code="${escapeHtml(a.code || "")}">
            <td class="mono-code">${escapeHtml(a.code || "—")}</td>
            <td class="coa-name-cell">
              <strong class="coa-name-display">${escapeHtml(a.name)}</strong>
              <input class="coa-name-input" type="text" value="${escapeHtml(a.name)}" style="display:none;width:100%" maxlength="200" />
            </td>
            <td>${coaTypePill(a.type)}</td>
            <td>${systemBadge}</td>
            <td><span class="pill ok" style="font-size:.72rem">Active</span></td>
            <td style="text-align:right;white-space:nowrap">
              <button class="secondary small" type="button" data-coa-action="edit-name" title="Edit name">&#9998;</button>
              <button class="secondary small" type="button" data-coa-action="save-name" style="display:none" title="Save">&#10003;</button>
              <button class="secondary small" type="button" data-coa-action="cancel-name" style="display:none" title="Cancel">&#10005;</button>
            </td>
          </tr>`;
      }).join("");

  return `
    <div class="verification-panel erp-workspace-panel" id="coa-workspace">
      <div class="preview-heading compact">
        <div>
          <h4>Chart of Accounts</h4>
          <p>${accounts.length} account${accounts.length !== 1 ? "s" : ""} in the ledger — account codes are permanent, only names can be edited.</p>
        </div>
        <button class="secondary" type="button" data-coa-action="toggle-add-form">+ Add Account</button>
      </div>

      <div id="coa-add-form" style="display:none" class="erp-form-inline">
        <h5 style="margin:0 0 .75rem">New Account</h5>
        <div style="display:grid;grid-template-columns:1fr 2fr 1fr 1fr;gap:.5rem .75rem;align-items:end">
          <label class="field-label">Code (optional)<input id="coa-new-code" type="text" maxlength="30" placeholder="e.g. 53099" /></label>
          <label class="field-label">Account Name *<input id="coa-new-name" type="text" maxlength="200" placeholder="e.g. Petty Cash" required /></label>
          <label class="field-label">Type *<select id="coa-new-type"><option value="">Select…</option>${typeOptions}</select></label>
          <label class="field-label">Classification *<select id="coa-new-class"><option value="">Select…</option>${classOptions}</select></label>
        </div>
        <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
          <button class="primary small" type="button" data-coa-action="submit-add">Create Account</button>
          <button class="secondary small" type="button" data-coa-action="toggle-add-form">Cancel</button>
          <span id="coa-add-msg" style="font-size:.8rem;margin-left:.5rem"></span>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap">
        <label class="field-label" style="margin:0;display:flex;align-items:center;gap:.5rem;flex-direction:row">
          <span style="white-space:nowrap;font-size:.82rem">Filter by Type</span>
          <select id="coa-type-filter" style="min-width:140px">
            <option value="" ${coaTypeFilter === "" ? "selected" : ""}>All Types</option>
            ${filterOptions}
          </select>
        </label>
        <span class="pill neutral" style="font-size:.75rem">${filtered.length} of ${accounts.length} account${accounts.length !== 1 ? "s" : ""}</span>
        ${coaTypeFilter ? `<button class="secondary small" type="button" data-coa-action="clear-filter">Clear filter</button>` : ""}
        <div id="coa-msg" style="font-size:.82rem;margin-left:auto"></div>
      </div>

      <div class="table-preview compact-table erp-table">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account Name</th>
              <th>Type</th>
              <th>System</th>
              <th>Status</th>
              <th style="text-align:right">Actions</th>
            </tr>
          </thead>
          <tbody id="coa-tbody">
            ${rows}
          </tbody>
        </table>
      </div>
    </div>`;
}

function coaShowMsg(el, text, ok) {
  if (!el) return;
  el.textContent = text;
  el.style.color = ok ? "var(--color-success, green)" : "var(--color-danger, red)";
  if (ok) setTimeout(() => { el.textContent = ""; }, 3000);
}

async function coaHandleAddSubmit() {
  const code = document.getElementById("coa-new-code")?.value.trim() || null;
  const name = document.getElementById("coa-new-name")?.value.trim() || "";
  const type = document.getElementById("coa-new-type")?.value;
  const classification = document.getElementById("coa-new-class")?.value;
  const msg = document.getElementById("coa-add-msg");

  if (!name || !type || !classification) {
    coaShowMsg(msg, "Name, Type and Classification are required.", false);
    return;
  }

  const body = { name, type, classification };
  if (code) body.code = code;

  const result = await apiRequest("mitrabooks", "/api/v1/accounting/accounts", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error creating account.`, false);
    return;
  }
  coaShowMsg(msg, "Account created.", true);
  ["coa-new-code", "coa-new-name"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  ["coa-new-type", "coa-new-class"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  await loadBusinessAccounts();
  dashboardPreview.innerHTML = renderBusinessWorkspace();
}

async function coaHandleSaveName(row) {
  const code = row.dataset.coaCode;
  const input = row.querySelector(".coa-name-input");
  const name = input?.value.trim() || "";
  const msg = document.getElementById("coa-msg");

  if (!name || name.length < 2) {
    coaShowMsg(msg, "Name must be at least 2 characters.", false);
    return;
  }

  const result = await apiRequest("mitrabooks", `/api/v1/accounting/accounts/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error updating account.`, false);
    return;
  }
  coaShowMsg(msg, `"${escapeHtml(name)}" saved.`, true);
  await loadBusinessAccounts();
  dashboardPreview.innerHTML = renderBusinessWorkspace();
}

function coaEnterEditMode(row) {
  row.querySelector(".coa-name-display").style.display = "none";
  row.querySelector(".coa-name-input").style.display = "";
  row.querySelector("[data-coa-action='edit-name']").style.display = "none";
  row.querySelector("[data-coa-action='save-name']").style.display = "";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "";
  row.querySelector(".coa-name-input").focus();
}

function coaExitEditMode(row) {
  const original = row.querySelector(".coa-name-display").textContent;
  row.querySelector(".coa-name-input").value = original;
  row.querySelector(".coa-name-display").style.display = "";
  row.querySelector(".coa-name-input").style.display = "none";
  row.querySelector("[data-coa-action='edit-name']").style.display = "";
  row.querySelector("[data-coa-action='save-name']").style.display = "none";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "none";
}

// ── End Chart of Accounts workspace ─────────────────────────────────────────


// ══════════════════════════════════════════════════════════════════════
// SECTION: FINANCIAL HEALTH WORKSPACE
// API   : GET /api/v1/business/financial-health?narrate=
// NOTE  : renderFinancialHealthWorkspace, fhFormatNarrative — AI narrative is advisory only
// ══════════════════════════════════════════════════════════════════════

function renderFinancialHealthWorkspace() {
  const data = lastFinancialHealth;

  // Lazy self-heal: fetch once whenever we render without data.
  if (!data && !financialHealthLoadInFlight) {
    setTimeout(() => { loadFinancialHealth(); }, 0);
  }

  if (!data) {
    return `
      <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
        <div class="preview-heading compact">
          <div><h4>Financial Health</h4><p>Loading ledger-backed insights…</p></div>
        </div>
      </section>`;
  }

  const kpis = (data.kpis || []).map(renderFhKpiCard).join("");
  const charts = (data.charts || []).map(renderFhBarChart).join("");
  const alerts = (data.alerts || []).map(renderFhAlert).join("");

  // AI narrative is advisory prose over the same trusted figures; render the
  // model's text as paragraphs/bullets with a clear "AI-generated" disclaimer.
  const narrativeCard = data.narrative
    ? `
      <div class="fh-narrative">
        <div class="fh-narrative-head"><span class="pill ok">AI summary</span><small>Generated from the figures below — verify before acting.</small></div>
        <div class="fh-narrative-body">${fhFormatNarrative(data.narrative)}</div>
      </div>`
    : "";

  return `
    <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Health</h4>
          <p>${escapeHtml(data.summary || "")}</p>
        </div>
        <button class="secondary" type="button" data-business-action="refresh-financial-health">Refresh</button>
      </div>
      ${narrativeCard}
      <div class="fh-kpi-grid">${kpis}</div>
      <div class="fh-section">
        <h5 class="fh-section-title">Alerts &amp; signals</h5>
        <ul class="fh-alerts">${alerts}</ul>
      </div>
      <div class="fh-charts-grid">${charts}</div>
      <p class="fh-footnote">As of ${escapeHtml(data.as_of || "")} · financial year from ${escapeHtml(data.financial_year_start || "")}. All figures computed from the posted ledger.</p>
    </section>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: PARTIES — CRUD + dialogs
// API   : GET/POST /api/v1/business/parties  PATCH .../deactivate
// NOTE  : loadBusinessParties, createBusinessParty, updateBusinessParty
// ══════════════════════════════════════════════════════════════════════

async function loadBusinessParties(filters = {}) {
  const appKey = "mitrabooks";
  const state = businessListState.parties;
  const params = new URLSearchParams();

  if (state.q) params.append("q", state.q);
  if (state.party_type) params.append("party_type", state.party_type);
  params.append("offset", state.offset || 0);
  params.append("limit", 20);

  const queryString = params.toString();
  const url = `/api/v1/business/parties${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  lastBusinessPartiesResult = result;
  if (result.ok) {
    lastBusinessParties = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "parties") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessParties = [];
    setLoginStatus("warn", "Unable to load parties", result.payload?.detail || "Check connection and try again.");
  }
  renderJson(apiOutput, { parties: { ok: result.ok, count: lastBusinessParties.length } });
  return result;
}

async function createBusinessParty(data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    party_type: data.party_type,
    gstin: data.gstin || null,
    pan: data.pan?.trim().toUpperCase() || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
  };

  const result = await apiRequest(appKey, "/api/v1/business/parties", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party created", result.payload?.party_name || "New party added.");
    document.getElementById("business-party-create-dialog")?.close();
    await loadBusinessParties();
    // Force refresh of current workspace
    if (activeBusinessWorkspace === "parties") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { create_party: result });
}

async function loadCaPracticeDocuments(options = {}) {
  const rerender = options?.rerender !== false;
  const params = new URLSearchParams({ limit: "100" });
  Object.entries(caPracticeFilters).forEach(([key, value]) => {
    const normalized = String(value || "").trim();
    if (normalized) {
      params.set(key, normalized);
    }
  });
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents?${params.toString()}`, { method: "GET" });
  lastCaDocumentsResult = result;
  if (result.ok) {
    lastCaDocuments = Array.isArray(result.payload?.items) ? result.payload.items : [];
    if (caDocumentAttachmentState.document_id) {
      const selected = lastCaDocuments.find((row) => row.document_id === caDocumentAttachmentState.document_id);
      if (selected) {
        caDocumentAttachmentState = {
          ...caDocumentAttachmentState,
          client_name: selected.client_name || caDocumentAttachmentState.client_name,
        };
      } else {
        caDocumentAttachmentState = { document_id: "", client_name: "", items: [], loading: false };
      }
    }
    if (rerender && currentExperience === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || activeBusinessWorkspace === "ca-access")) {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (activeBusinessWorkspace === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    }
  } else {
    lastCaDocuments = [];
    setLoginStatus("warn", "Unable to load CA documents", statusDetailText(result.payload?.detail) || `Document metadata request failed with HTTP ${result.status}.`);
    if (rerender && currentExperience === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || activeBusinessWorkspace === "ca-access")) {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (activeBusinessWorkspace === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    }
  }
  renderJson(apiOutput, { ca_documents: { ok: result.ok, status: result.status, count: lastCaDocuments.length, detail: result.payload?.detail || null } });
  return result;
}

async function loadCaClients(options = {}) {
  const rerender = options?.rerender !== false;
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-clients?active_only=true&limit=100", { method: "GET" });
  lastCaClientsResult = result;
  if (result.ok) {
    lastCaClients = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    lastCaClients = [];
    setLoginStatus("warn", "Unable to load CA clients", statusDetailText(result.payload?.detail) || `CA client request failed with HTTP ${result.status}.`);
  }
  if (rerender) {
    rerenderCaPracticeIfActive();
  }
  return result;
}

function rerenderCaPracticeIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "ca-access") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadCaAccessUsers(options = {}) {
  const rerender = options?.rerender !== false;
  caAccessLoading = true;
  if (rerender && activeBusinessWorkspace === "ca-access") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca/users", { method: "GET" });
  caAccessLoading = false;
  if (result.ok) {
    caAccessUsers = Array.isArray(result.payload?.ca_users) ? result.payload.ca_users : [];
  } else {
    caAccessUsers = [];
  }
  if (rerender && activeBusinessWorkspace === "ca-access") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
  return result;
}

async function createCaPracticeDocument(form) {
  const formData = new FormData(form);
  const selectedFiles = Array.from(form.querySelector("[name='ca_attachments']")?.files || []);
  const selectedClientId = String(formData.get("client_id") || "").trim();
  const selectedClient = caClientById(selectedClientId);
  const payload = {
    client_id: selectedClientId || null,
    client_name: String(formData.get("client_name") || selectedClient?.client_name || "").trim(),
    document_type: String(formData.get("document_type") || "").trim(),
    period: String(formData.get("period") || "").trim(),
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    client_owner: String(formData.get("client_owner") || "").trim() || null,
    priority: String(formData.get("priority") || "normal").trim() || "normal",
    due_date: String(formData.get("due_date") || "").trim() || null,
    compliance_area: String(formData.get("compliance_area") || "").trim() || null,
    client_access_enabled: formData.get("client_access_enabled") === "true",
    original_file_name: String(formData.get("original_file_name") || "").trim() || selectedFiles[0]?.name || null,
    notes: String(formData.get("notes") || "").trim() || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    form.reset();
    const documentId = result.payload?.document_id || "";
    if (documentId) {
      caDocumentAttachmentState = {
        document_id: documentId,
        client_name: result.payload?.client_name || payload.client_name,
        items: [],
        loading: false,
      };
    }
    await loadCaPracticeDocuments();
    let uploadResults = [];
    if (documentId) {
      if (selectedFiles.length) {
        uploadResults = await uploadBusinessAttachmentFiles("ca_document", documentId, selectedFiles);
        await loadCaPracticeDocuments({ rerender: false });
      }
      await loadCaDocumentAttachments(documentId, result.payload?.client_name || payload.client_name);
    }
    const successCount = uploadResults.filter((item) => item.ok).length;
    const failureCount = uploadResults.length - successCount;
    if (!uploadResults.length) {
      setLoginStatus("ok", "Document metadata added", `${result.payload?.client_name || "Client"} is now in the CA review queue.`);
    } else if (failureCount === 0) {
      setLoginStatus("ok", "Document metadata added", `${result.payload?.client_name || "Client"} was created with ${successCount} attachment(s).`);
    } else if (successCount > 0) {
      setLoginStatus("warn", "Document added with partial file upload", `${successCount} attachment(s) uploaded and ${failureCount} failed. Refresh the file panel for details.`);
    } else {
      setLoginStatus("warn", "Document added but files failed", `${result.payload?.client_name || "Client"} was created, but the attachment upload failed.`);
    }
  } else {
    setLoginStatus("danger", "Document create failed", statusDetailText(result.payload?.detail) || "Check the required fields and try again.");
  }
  renderJson(apiOutput, { create_ca_document: result });
}

async function createCaClient(form) {
  const formData = new FormData(form);
  const complianceTracks = String(formData.get("compliance_tracks") || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const payload = {
    client_name: String(formData.get("client_name") || "").trim(),
    gstin: String(formData.get("gstin") || "").trim() || null,
    pan: String(formData.get("pan") || "").trim() || null,
    contact_person: String(formData.get("contact_person") || "").trim() || null,
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    client_owner: String(formData.get("client_owner") || "").trim() || null,
    engagement_type: String(formData.get("engagement_type") || "").trim() || null,
    access_level: String(formData.get("access_level") || "view_only").trim() || "view_only",
    compliance_tracks: complianceTracks,
    notes: String(formData.get("notes") || "").trim() || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-clients", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    caClientDraft = {
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
    form.reset();
    await loadCaClients();
    setLoginStatus("ok", "CA client added", `${result.payload?.client_name || "Client"} is now available in the CA practice workspace.`);
  } else {
    setLoginStatus("danger", "CA client create failed", statusDetailText(result.payload?.detail) || "Check the required fields and try again.");
  }
  renderJson(apiOutput, { create_ca_client: result });
}

async function loadCaDocumentAttachments(documentId, clientName = "") {
  if (!documentId) {
    caDocumentAttachmentState = { document_id: "", client_name: "", items: [], loading: false };
    rerenderCaPracticeIfActive();
    return { ok: false, status: 0, payload: { detail: "Missing document id." } };
  }
  caDocumentAttachmentState = {
    document_id: documentId,
    client_name: clientName || caDocumentAttachmentState.client_name,
    items: caDocumentAttachmentState.document_id === documentId ? caDocumentAttachmentState.items : [],
    loading: true,
  };
  rerenderCaPracticeIfActive();
  const result = await listBusinessAttachments("ca_document", documentId);
  caDocumentAttachmentState = {
    document_id: documentId,
    client_name: clientName || caDocumentAttachmentState.client_name,
    items: result.ok ? (Array.isArray(result.payload?.items) ? result.payload.items : []) : [],
    loading: false,
  };
  if (!result.ok) {
    setLoginStatus("warn", "Unable to load CA document files", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  rerenderCaPracticeIfActive();
  renderJson(apiOutput, { ca_document_attachments: { ok: result.ok, status: result.status, count: caDocumentAttachmentState.items.length } });
  return result;
}

async function updateCaPracticeDocumentStatus(documentId, status) {
  if (!documentId || !status) {
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents/${encodeURIComponent(documentId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Document status updated", `${result.payload?.client_name || "Document"} marked ${caDocumentStatusLabel(status)}.`);
    await loadCaPracticeDocuments();
  } else {
    setLoginStatus("danger", "Status update failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { update_ca_document: result });
}

async function updateBusinessParty(partyId, data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    gstin: data.gstin || null,
    pan: data.pan?.trim().toUpperCase() || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
  };
  if (data.party_type) {
    payload.party_type = data.party_type;
  }

  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party updated", result.payload?.party_name || "Changes saved.");
    document.getElementById("business-party-edit-dialog")?.close();
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Update party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { update_party: result });
}

async function deactivateBusinessParty(partyId) {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}/deactivate`, {
    method: "POST",
  });

  if (result.ok) {
    setLoginStatus("ok", "Party deactivated", "Party is now inactive.");
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Deactivate party failed", result.payload?.detail || "Try again.");
  }
  renderJson(apiOutput, { deactivate_party: result });
}

function openBusinessCreatePartyDialog() {
  const dialog = document.getElementById("business-party-create-dialog");
  const form = document.getElementById("business-party-create-form");
  if (!form) return;

  form.reset();
  dialog?.showModal();
}

function openBusinessEditPartyDialog(button) {
  const dialog = document.getElementById("business-party-edit-dialog");
  const form = document.getElementById("business-party-edit-form");
  if (!form) return;

  const partyId = button.getAttribute("data-party-id") || "";
  const partyName = button.getAttribute("data-party-name") || "";
  const partyType = button.getAttribute("data-party-type") || "customer";
  const partyGstin = button.getAttribute("data-party-gstin") || "";
  const partyPan = button.getAttribute("data-party-pan") || "";
  const partyCity = button.getAttribute("data-party-city") || "";
  const partyState = button.getAttribute("data-party-state") || "";
  const partyPincode = button.getAttribute("data-party-pincode") || "";

  document.getElementById("business-party-edit-id").value = partyId;
  const editTypeSelect = document.getElementById("business-party-edit-type");
  if (editTypeSelect) editTypeSelect.value = partyType;
  document.getElementById("business-party-edit-name").value = partyName;
  document.getElementById("business-party-edit-gstin").value = partyGstin;
  const editPanInput = document.getElementById("business-party-edit-pan");
  if (editPanInput) editPanInput.value = partyPan;
  document.getElementById("business-party-edit-city").value = partyCity;
  document.getElementById("business-party-edit-state").value = partyState;
  document.getElementById("business-party-edit-pincode").value = partyPincode;
  document.getElementById("business-party-edit-label").textContent = `Editing ${partyName}`;

  dialog?.showModal();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS WORKSPACE ROUTER — state + navigation
// NOTE  : setBusinessWorkspace, syncBusinessNavActiveState — drives activeBusinessWorkspace
// ══════════════════════════════════════════════════════════════════════

function setBusinessWorkspace(workspace) {
  if (currentExperience === "mitrabooks" && activeOrgSelectorType() !== "BUSINESS") {
    selectedOrgType = "BUSINESS";
    updateTrustedContextUi();
  }
  if (workspace !== "settings") {
    activeSettingsDetailId = "";
  }
  activeBusinessWorkspace = workspace;
  syncBusinessNavActiveState();
  dashboardPreview.innerHTML = workspace === "overview"
    ? renderDashboardPreview(experienceConfig.mitrabooks)
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
    if (workspace === "gst-returns") businessReportState.tab = "gst-returns";
    else if (workspace === "reconciliation") businessReportState.tab = "payment-allocation";
    else if (workspace === "tds-tcs") businessReportState.tab = "tds";
    else if (workspace === "bank-recon") businessReportState.tab = "bank-recon";
    loadBusinessAccounts();
    refreshCurrentBusinessReport();
  } else if (workspace === "sales") {
    salesUi.view = "list";
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
    purchaseUi.view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadBusinessBills();
  } else if (workspace === "credit-notes") {
    creditUi.view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadCreditNotes();
  } else if (workspace === "debit-notes") {
    debitUi.view = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadDebitNotes();
  } else if (workspace === "coa") {
    coaTypeFilter = "";
    loadBusinessAccounts();
  } else if (workspace === "ca-access") {
    lastCaDocumentsResult = null;
    lastCaDocuments = [];
    lastCaClientsResult = null;
    lastCaClients = [];
    caAccessUsers = [];
    caInviteError = "";
    caInviteSuccess = "";
    const startupLoads = [];
    if (isBusinessAdmin()) {
      startupLoads.push(loadCaAccessUsers({ rerender: false }));
    }
    startupLoads.push(loadCaClients({ rerender: false }));
    startupLoads.push(loadCaPracticeDocuments({ rerender: false }));
    Promise.allSettled(startupLoads).then(() => {
      if (activeBusinessWorkspace === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    });
  } else if (workspace === "hr") {
    hrUi.tab = "employees";
    hrUi.error = "";
    hrUi.selectedRunId = "";
    hrUi.runSlips = [];
    loadHrWorkspace();
  } else if (workspace === "manufacturing") {
    mfgTab = "cost-centres";
    mfgError = "";
    loadMfgWorkspace();
  }
}

function syncBusinessNavActiveState() {
  const selectorOrgType = activeOrgSelectorType();
  const isPlannedOrgWorkspace = currentExperience === "mitrabooks"
    && activeBusinessWorkspace === "overview"
    && selectorOrgType !== "BUSINESS";
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.businessWorkspace || "";
    const isActive = currentExperience === "mitrabooks"
      && !isPlannedOrgWorkspace
      && workspace
      && workspace === activeBusinessWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "mitrabooks") {
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
      "gst-returns": "GST Returns",
      "reconciliation": "Reconciliation",
      "tds-tcs": "TDS / TCS",
      "bank-recon": "Bank Reconciliation",
      "ca-access": "CA Practice Portal",
      coa: "Chart of Accounts",
      settings: "Settings",
    };
    const plannedMeta = orgSelectorMeta[selectorOrgType];
    const label = isPlannedOrgWorkspace
      ? plannedMeta?.label || "Planned Workspace"
      : labels[activeBusinessWorkspace] || "Dashboard";
    topbarCurrent.textContent = label;
    updatePageHeader("MitraBooks", label, `${label} Workspace`);
  }
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS LIST FILTERING + PAGINATION
// NOTE  : applyBusinessListFilter, resetBusinessListFilter, pageBusinessList
// ══════════════════════════════════════════════════════════════════════

function applyBusinessListFilter(listKind) {
  if (listKind === "parties") {
    const panel = document.querySelector("[data-business-list='parties']");
    if (!panel) return;

    const qInput = panel.querySelector("input[name='q']");
    const typeInput = panel.querySelector("select[name='party_type']");

    businessListState.parties.q = qInput?.value || "";
    businessListState.parties.party_type = typeInput?.value || "";
    businessListState.parties.offset = 0;

    loadBusinessParties();
  } else if (listKind === "vouchers") {
    const panel = document.querySelector("[data-business-list='vouchers']");
    if (!panel) return;

    const voucherTypeInput = panel.querySelector("select[name='voucher_type']");
    const statusInput = panel.querySelector("select[name='status']");
    const approvalInput = panel.querySelector("select[name='approval_status']");

    businessListState.vouchers.voucher_type = voucherTypeInput?.value || "";
    businessListState.vouchers.status = statusInput?.value || "";
    businessListState.vouchers.approval_status = approvalInput?.value || "";
    businessListState.vouchers.offset = 0;

    loadBusinessVouchers();
  }
}

function resetBusinessListFilter(listKind) {
  if (listKind === "parties") {
    businessListState.parties = {
      offset: 0,
      q: "",
      party_type: "",
      from_date: "",
      to_date: "",
    };
    loadBusinessParties();
  } else if (listKind === "vouchers") {
    businessListState.vouchers = {
      offset: 0,
      voucher_type: "",
      status: "",
      approval_status: "",
      include_reviewed: false,
    };
    loadBusinessVouchers();
  }
}

function pageBusinessList(listKind, direction) {
  if (listKind === "parties") {
    const offset = Number(businessListState.parties.offset || 0);
    businessListState.parties.offset = direction === "next" ? offset + 20 : Math.max(0, offset - 20);
    loadBusinessParties();
  } else if (listKind === "vouchers") {
    const offset = Number(businessListState.vouchers.offset || 0);
    businessListState.vouchers.offset = direction === "next" ? offset + 20 : Math.max(0, offset - 20);
    loadBusinessVouchers();
  }
}

// ========== Business Module: Financial Reports ==========

const BUSINESS_REPORT_TABS = [
  { id: "trial-balance", label: "Trial Balance" },
  { id: "pnl", label: "Profit & Loss" },
  { id: "balance-sheet", label: "Balance Sheet" },
  { id: "general-ledger", label: "General Ledger" },
  { id: "receivables-payables", label: "Receivables / Payables" },
  { id: "aging", label: "AR/AP Aging" },
  { id: "statements", label: "Statements" },
  { id: "payment-allocation", label: "Payment Allocation" },
  { id: "gst-settlement", label: "GST Settlement" },
  { id: "gst-returns", label: "GST Returns" },
  { id: "tds", label: "TDS / TCS" },
  { id: "bank-recon", label: "Bank Reconciliation" },
  { id: "bank-cash-book", label: "Bank / Cash Book" },
  { id: "opening-yearend", label: "Opening & Year-End" },
  { id: "fixed-assets", label: "Fixed Assets" },
  { id: "dimensions", label: "Dimensions" },
  { id: "inventory", label: "Inventory" },
  { id: "itc-reversals", label: "ITC Reversals" },
  { id: "period-locks", label: "Period Locks" },
];




// Current Indian financial year as "YYYY-YY" (FY starts April).
function currentFinancialYear() {
  const d = new Date();
  const startYear = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
  return `${startYear}-${String(startYear + 1).slice(-2)}`;
}

function recentFinancialYears(count = 4) {
  let startYear = Number(currentFinancialYear().slice(0, 4));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${startYear}-${String(startYear + 1).slice(-2)}`);
    startYear -= 1;
  }
  return out;
}

// Current Indian-FY quarter as "YYYY-Q[1-4]" (FY starts April; Q1 = Apr-Jun).
function currentFyQuarter() {
  const d = new Date();
  const m = d.getMonth(); // 0-11
  const y = d.getFullYear();
  if (m >= 3 && m <= 5) return `${y}-Q1`;
  if (m >= 6 && m <= 8) return `${y}-Q2`;
  if (m >= 9 && m <= 11) return `${y}-Q3`;
  return `${y - 1}-Q4`;       // Jan-Mar belongs to the FY that started the prior April
}

// A handful of recent FY quarters for the CMP-08 picker.
function recentFyQuarters(count = 6) {
  const cur = currentFyQuarter();
  let [fy, q] = cur.split("-Q").map((x, i) => (i === 0 ? Number(x) : Number(x)));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${fy}-Q${q}`);
    q -= 1;
    if (q < 1) { q = 4; fy -= 1; }
  }
  return out;
}

function financialYearStartIso() {
  const now = new Date();
  // Indian financial year starts April 1. Jan-Mar (month index 0-2) belong to the prior FY.
  const year = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  return `${year}-04-01`;
}

const businessReportState = {
  tab: "trial-balance",
  as_of: todayIsoDate(),
  from_date: financialYearStartIso(),
  to_date: todayIsoDate(),
  ledgerAccountId: "",
  agingKind: "receivable",
};


// ══════════════════════════════════════════════════════════════════════
// SECTION: FINANCIAL REPORTS — workspace renderer + report framework
// API   : GET /api/v1/business/reports/... (all report tabs)
// NOTE  : refreshCurrentBusinessReport, reportResultPayload — dispatches to tab-specific renderers
// ══════════════════════════════════════════════════════════════════════

function reportResultPayload(result, extra = {}) {
  if (result.ok) {
    return { ok: true, ...(result.payload || {}), ...extra };
  }
  return { ok: false, status: result.status, detail: result.payload?.detail || null, ...extra };
}

async function refreshCurrentBusinessReport() {
  const tab = businessReportState.tab;
  if (tab === "trial-balance") {
    await loadBusinessTrialBalance();
  } else if (tab === "pnl") {
    await loadBusinessProfitLoss();
  } else if (tab === "balance-sheet") {
    await loadBusinessBalanceSheet();
  } else if (tab === "receivables-payables") {
    await loadBusinessReceivablesPayables();
  } else if (tab === "aging") {
    await loadBusinessAging();
  } else if (tab === "payment-allocation") {
    await loadUnallocatedPayments();
    await loadAllocationReconciliation();
  } else if (tab === "general-ledger") {
    if (businessReportState.ledgerAccountId === "__all_nonzero__") {
      await loadBusinessAllLedgers();
    } else if (businessReportState.ledgerAccountId) {
      await loadBusinessGeneralLedger(businessReportState.ledgerAccountId);
    } else {
      rerenderBusinessReportsIfActive();
    }
  } else if (tab === "period-locks") {
    await loadPeriodLocks();
  } else if (tab === "gst-settlement") {
    await loadGstSettlementPreview(gstReturnState.gstSettlementPeriod);
  } else if (tab === "gst-returns") {
    if (gstReturnState.gstReturnType === "gstr1") { await loadGstr1(gstReturnState.gstr3bPeriod); }
    else if (gstReturnState.gstReturnType === "cmp08") { await loadCmp08(gstReturnState.cmp08Quarter); }
    else if (gstReturnState.gstReturnType === "gstr4") { await loadGstr4(gstReturnState.gstr4Fy); }
    else if (gstReturnState.gstReturnType === "gstr2b") { rerenderBusinessReportsIfActive(); }  // upload-driven
    else { await loadGstr3b(gstReturnState.gstr3bPeriod); }
  } else if (tab === "itc-reversals") {
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (tab === "tds") {
    await loadTdsRegister(tdsQuarter);
  } else if (tab === "bank-recon") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    if (bankReconAccountId) await loadBankReconciliation(bankReconAccountId);
    else rerenderBusinessReportsIfActive();
  } else if (tab === "bank-cash-book") {
    await loadBankCashBook();
  } else if (tab === "statements") {
    if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) await loadBusinessParties();
    if (statementPartyId) await loadPartyStatement();
    else rerenderBusinessReportsIfActive();
  } else if (tab === "opening-yearend") {
    // Workflow tab — both halves load on demand (Preview buttons).
    rerenderBusinessReportsIfActive();
  } else if (tab === "fixed-assets") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    await loadFixedAssets();
  } else if (tab === "dimensions") {
    await loadDimensions();
    await loadDimensionReport();
    await loadBranchConsolidatedReport();
  } else if (tab === "inventory") {
    await loadInventoryItems();
    if (lastInventoryItems?.inventory_enabled) {
      await loadInventoryPolicy();
      await loadStockMovements();
      await loadStockRegister();
      await loadClosingStockEntries();
    } else {
      rerenderBusinessReportsIfActive();
    }
  }
}




function rerenderBusinessReportsIfActive() {
  const reportWorkspaces = ["reports", "gst-returns", "reconciliation", "tds-tcs", "bank-recon"];
  if (currentExperience === "mitrabooks" && reportWorkspaces.includes(activeBusinessWorkspace)) {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}


function reportExportToolbar(reportKey, { kind = "", label = "" } = {}) {
  const kAttr = kind ? ` data-report-kind="${escapeHtml(kind)}"` : "";
  const key = escapeHtml(reportKey);
  const lbl = label ? `<span class="export-label muted">${escapeHtml(label)}</span>` : "";
  const tallyXml = reportKey === "trial_balance"
    ? `<button class="secondary" type="button" data-business-action="export-tally-xml">Tally XML</button>`
    : "";
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
      ${lbl}
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="csv"${kAttr}>CSV</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="xlsx"${kAttr}>Excel</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="pdf"${kAttr}>PDF</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="json"${kAttr}>JSON</button>
      ${tallyXml}
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

// Export/print toolbars per report tab. Backend supports CSV/XLSX/PDF for the
// core set (trial_balance, party_ledger, itc_reversals, aging, balance_sheet,
// profit_loss); other tabs get Print only for now.
function businessReportExports() {
  const tab = businessReportState.tab;
  if (tab === "trial-balance") return reportExportToolbar("trial_balance");
  if (tab === "balance-sheet") return reportExportToolbar("balance_sheet");
  if (tab === "pnl") return reportExportToolbar("profit_loss");
  if (tab === "aging") return reportExportToolbar("aging", { kind: businessReportState.agingKind });
  if (tab === "payment-allocation") return "";  // workflow screen has its own controls
  if (tab === "itc-reversals") return reportExportToolbar("itc_reversals");
  if (tab === "statements") {
    return statementPartyId ? reportExportToolbar("statement", { kind: statementKind }) : "";
  }
  if (tab === "receivables-payables") {
    return `
      ${reportExportToolbar("party_ledger", { kind: "receivable", label: "Debtors:" })}
      ${reportExportToolbar("party_ledger", { kind: "payable", label: "Creditors:" })}`;
  }
  if (tab === "general-ledger") {
    const acc = businessReportState.ledgerAccountId;
    if (acc && acc !== "__all_nonzero__") {
      return reportExportToolbar("general_ledger");
    }
    return `
      <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
        <span class="muted">Select a single account to download (CSV/Excel/PDF). "All Ledger Accounts" supports Print only.</span>
        <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
      </div>`;
  }
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;margin:8px 0;">
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

async function downloadBusinessReport(reportKey, format, kind) {
  if (!reportKey) return;
  const params = new URLSearchParams();
  params.set("report", reportKey);
  params.set("format", format || "csv");
  if (kind) params.set("kind", kind);
  if (businessReportState.as_of) params.set("as_of", businessReportState.as_of);
  if (reportKey === "profit_loss") {
    if (businessReportState.from_date) params.set("from_date", businessReportState.from_date);
    if (businessReportState.to_date) params.set("to_date", businessReportState.to_date);
  }
  if (reportKey === "general_ledger") {
    const acc = businessReportState.ledgerAccountId;
    if (!acc || acc === "__all_nonzero__") {
      renderJson(apiOutput, { export_error: { report: reportKey, detail: "Select a single ledger account before downloading." } });
      return;
    }
    params.set("account_id", acc);
  }
  if (reportKey === "statement") {
    if (!statementPartyId) {
      renderJson(apiOutput, { export_error: { report: reportKey, detail: "Select a party before downloading the statement." } });
      return;
    }
    params.set("party_id", statementPartyId);
    params.set("kind", statementKind);
    if (statementFromDate) params.set("from_date", statementFromDate);
    if (statementToDate) params.set("to_date", statementToDate);
  }
  const periodStamp = reportKey === "profit_loss"
    ? `${businessReportState.from_date}_${businessReportState.to_date}`
    : businessReportState.as_of;
  const filename = `${reportKey}${kind ? "_" + kind : ""}_${periodStamp}.${format || "csv"}`;
  const path = `/api/v1/business/reports/export?${params.toString()}`;
  const result = await downloadApiFile("mitrabooks", path, filename, { timeoutMs: 30000 });
  if (result.ok) {
    renderJson(apiOutput, { export: { report: reportKey, format, kind: kind || null, filename } });
  } else {
    renderJson(apiOutput, { export_error: { report: reportKey, format, status: result.status, detail: result.payload?.detail || result.payload } });
  }
}

async function downloadTallyXmlExport() {
  const params = new URLSearchParams();
  if (businessReportState.as_of) params.set("as_of", businessReportState.as_of);
  const filename = `tally_trial_balance_${businessReportState.as_of || todayIsoDate()}.xml`;
  const result = await downloadApiFile("mitrabooks", `/api/v1/business/tally/xml-export?${params.toString()}`, filename, { timeoutMs: 30000 });
  if (result.ok) {
    renderJson(apiOutput, { tally_xml_export: { report: "trial_balance", filename } });
  } else {
    renderJson(apiOutput, { tally_xml_export_error: { status: result.status, detail: result.payload?.detail || result.payload } });
  }
}

// Print the currently rendered report by cloning its HTML into a clean window —
// avoids fighting the app's global/screen CSS and works across browsers
// (the user picks "Save as PDF" there too if they prefer a browser-rendered PDF).
function printBusinessReport() {
  const node = document.getElementById("business-report-printable");
  if (!node) { window.print(); return; }
  const win = window.open("", "_blank", "width=940,height=720");
  if (!win) { window.print(); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Financial Report</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;}
      h3,h4{margin:0 0 6px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 18px;}
      th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      td.amount,th.amount,.amount,.num,td.right{text-align:right;}
      .muted{color:#666;font-size:11px;}
      button,.report-export-toolbar,.report-tabs,.report-date-controls,input,select{display:none!important;}
    </style></head><body>${node.innerHTML}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { try { win.print(); } catch (_e) {} }, 300);
}

function downloadJsonObject(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function printBusinessDocumentDetail(title, selector) {
  const node = document.querySelector(selector);
  if (!node) { window.print(); return; }
  const win = window.open("", "_blank", "width=940,height=720");
  if (!win) { window.print(); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;}
      h3,h4{margin:0 0 6px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 18px;}
      th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      td.amount,th.amount,.amount,.num,td.right{text-align:right;}
      .muted{color:#666;font-size:11px;}
      button,.invoice-detail-actions,.reversal-panel,input,select{display:none!important;}
    </style></head><body>${node.innerHTML}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { try { win.print(); } catch (_e) {} }, 300);
}

function downloadCreditNoteJson() {
  if (!creditUi.detail) {
    renderJson(apiOutput, { credit_note_export_error: { detail: "Open a credit note before exporting." } });
    return;
  }
  const filename = `${creditUi.detail.credit_note_number || creditUi.detail.credit_note_id || "credit_note"}.json`;
  downloadJsonObject(creditUi.detail, filename);
  renderJson(apiOutput, { credit_note_export: { format: "json", filename } });
}

function downloadDebitNoteJson() {
  if (!debitUi.detail) {
    renderJson(apiOutput, { debit_note_export_error: { detail: "Open a debit note before exporting." } });
    return;
  }
  const filename = `${debitUi.detail.debit_note_number || debitUi.detail.debit_note_id || "debit_note"}.json`;
  downloadJsonObject(debitUi.detail, filename);
  renderJson(apiOutput, { debit_note_export: { format: "json", filename } });
}

function printCreditNoteDetail() {
  printBusinessDocumentDetail("Credit Note", "[data-credit-note-printable]");
  renderJson(apiOutput, { credit_note_print: { ok: true } });
}

function printDebitNoteDetail() {
  printBusinessDocumentDetail("Debit Note", "[data-debit-note-printable]");
  renderJson(apiOutput, { debit_note_print: { ok: true } });
}

function renderBusinessReportsWorkspace() {
  const tabs = BUSINESS_REPORT_TABS.map((tab) => `
    <button
      class="report-tab ${businessReportState.tab === tab.id ? "active" : ""}"
      type="button"
      data-business-action="report-tab"
      data-report-tab="${escapeHtml(tab.id)}"
    >${escapeHtml(tab.label)}</button>
  `).join("");

  let body = "";
  if (businessReportState.tab === "trial-balance") {
    body = renderBusinessTrialBalance();
  } else if (businessReportState.tab === "pnl") {
    body = renderBusinessProfitLoss();
  } else if (businessReportState.tab === "balance-sheet") {
    body = renderBusinessBalanceSheet();
  } else if (businessReportState.tab === "general-ledger") {
    body = renderBusinessGeneralLedger();
  } else if (businessReportState.tab === "receivables-payables") {
    body = renderBusinessReceivablesPayables();
  } else if (businessReportState.tab === "aging") {
    body = renderBusinessAging();
  } else if (businessReportState.tab === "payment-allocation") {
    body = renderPaymentAllocation();
  } else if (businessReportState.tab === "period-locks") {
    body = renderPeriodLocksPanel();
  } else if (businessReportState.tab === "gst-settlement") {
    body = renderGstSettlementPanel();
  } else if (businessReportState.tab === "gst-returns") {
    body = renderGstReturns();
  } else if (businessReportState.tab === "itc-reversals") {
    body = renderItcReversalPanel();
  } else if (businessReportState.tab === "tds") {
    body = renderTdsRegisterPanel();
  } else if (businessReportState.tab === "bank-recon") {
    body = renderBankReconPanel();
  } else if (businessReportState.tab === "bank-cash-book") {
    body = renderBankCashBookPanel();
  } else if (businessReportState.tab === "statements") {
    body = renderStatementsPanel();
  } else if (businessReportState.tab === "opening-yearend") {
    body = renderOpeningYearEndPanel();
  } else if (businessReportState.tab === "fixed-assets") {
    body = renderFixedAssetsPanel();
  } else if (businessReportState.tab === "dimensions") {
    body = renderDimensionsPanel();
  } else if (businessReportState.tab === "inventory") {
    body = renderInventoryPanel();
  }

  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Reports</h4>
          <p>Live reports from posted ledger entries for this tenant.</p>
        </div>
      </div>
      <div class="report-tabs" role="tablist">${tabs}</div>
      ${reportDateControls()}
      ${businessReportExports()}
      <div id="business-report-printable">${body}</div>
    </div>
  `;
}

function reportUnavailablePanel(title, payload) {
  const detail = payload?.detail || "Report unavailable. Check accounting access and try again.";
  return `
    <div class="table-preview compact-table">
      <h4>${escapeHtml(title)}</h4>
      <p class="muted">${escapeHtml(detail)}</p>
    </div>
  `;
}

// TDS/TCS section masters from GET /business/tds/sections (cached per session).
let tdsSectionsCache = null;
async function loadTdsSections() {
  if (tdsSectionsCache) return tdsSectionsCache;
  const result = await apiRequest("mitrabooks", "/api/v1/business/tds/sections", { method: "GET" });
  if (result.ok) tdsSectionsCache = result.payload;
  return tdsSectionsCache;
}

function tdsSectionRate(kind, section) {
  const rows = tdsSectionsCache?.[kind] || [];
  const hit = rows.find((r) => r.section === section);
  return hit ? Number(hit.rate) : 0;
}

function tdsSectionOptions(kind, selected) {
  const rows = tdsSectionsCache?.[kind] || [];
  const none = `<option value="">No ${kind === "tds" ? "TDS" : "TCS"}</option>`;
  return none + rows.map((r) =>
    `<option value="${escapeHtml(r.section)}" ${r.section === selected ? "selected" : ""}>${escapeHtml(`${r.section} · ${r.label} @ ${r.rate}%`)}</option>`
  ).join("");
}


function isBusinessAdmin() {
  const role = String(lastModuleContext?.role || lastModuleContext?.user_role || "").trim().toLowerCase();
  // Show settings to admins; when role is unknown the backend still enforces access on save.
  return role === "" || role === "tenant_admin" || role === "super_admin";
}

function isCaViewer() {
  const role = String(lastModuleContext?.role || lastModuleContext?.user_role || "").trim().toLowerCase();
  return role === "ca_viewer";
}





async function loadBusinessAdminSettings() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/admin-settings", { method: "GET" });
  if (result.ok) {
    lastBusinessAdminSettings = result.payload || buildBusinessAdminSettingsPayload();
  } else if (!lastBusinessAdminSettings) {
    lastBusinessAdminSettings = buildBusinessAdminSettingsPayload();
    setLoginStatus("danger", "Unable to load admin settings", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "settings") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function saveBusinessAdminSettingsSection(sectionKey) {
  const editor = document.querySelector(`[data-settings-json="${sectionKey}"]`);
  if (!editor) return;
  let parsed = {};
  try {
    parsed = JSON.parse(editor.value || "{}");
  } catch (error) {
    setLoginStatus("warn", "Invalid settings JSON", error?.message || "Fix the JSON before saving.");
    return;
  }
  const payload = buildBusinessAdminSettingsPayload(lastBusinessAdminSettings || {});
  payload[sectionKey] = parsed;
  const result = await apiRequest("mitrabooks", "/api/v1/business/admin-settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    lastBusinessAdminSettings = result.payload || payload;
    setLoginStatus("ok", "Settings saved", "The selected settings section was saved for the current MitraBooks tenant.");
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "settings") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Save failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
}

function round2(value) {
  const n = Number(value);
  if (!isFinite(n)) return 0;
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// Reversal must stay within the document's GST month. Returns the date input
// bounds + a sensible default (today if in-month, else month end).
function reversalDateBounds(isoDate) {
  const d = String(isoDate || todayIsoDate());
  const ym = d.slice(0, 7);
  const [y, m] = ym.split("-").map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  const start = `${ym}-01`;
  const end = `${ym}-${String(lastDay).padStart(2, "0")}`;
  const today = todayIsoDate();
  const inMonth = today.slice(0, 7) === ym;
  return { min: start, max: inMonth ? today : end, def: inMonth ? today : end, label: ym };
}

function reversalPanel(kind, id, isoDate) {
  const b = reversalDateBounds(isoDate);
  return `
    <div class="reversal-panel">
      <label>Reversal date
        <input type="date" data-reversal-date value="${escapeHtml(b.def)}" min="${escapeHtml(b.min)}" max="${escapeHtml(b.max)}">
      </label>
      <div class="reversal-panel-actions">
        <button class="primary" type="button" data-business-action="confirm-reverse-${kind}" data-${kind}-id="${escapeHtml(id)}">Confirm reverse</button>
        <button class="secondary" type="button" data-business-action="cancel-reverse-${kind}">Cancel</button>
      </div>
      <p class="muted">Must be dated within the document's GST month (${escapeHtml(b.label)}). A reversing journal entry will be posted on this date.</p>
      <p class="muted reversal-scope-note">Use reverse only to correct an entry made in error in the open period. For returns, price changes, or ITC reversal, raise a ${kind === "bill" ? "debit note" : "credit note"} instead (coming soon).</p>
    </div>
  `;
}






function focusBusinessEntryField(selector) {
  setTimeout(() => {
    const field = document.querySelector(selector);
    if (field) {
      field.focus();
    }
  }, 0);
}


















function renderBusinessVouchersListFilters(rowsLength) {
  const state = businessListState.vouchers;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 20) : 0;
  const nextDisabled = rowsLength < 20 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="vouchers">
      <div class="list-filter-bar">
        <label class="field">
          <span>Type</span>
          <select name="voucher_type">
            <option value="">All types</option>
            <option value="payment" ${state.voucher_type === "payment" ? "selected" : ""}>Payment</option>
            <option value="receipt" ${state.voucher_type === "receipt" ? "selected" : ""}>Receipt</option>
            <option value="contra" ${state.voucher_type === "contra" ? "selected" : ""}>Contra</option>
            <option value="journal" ${state.voucher_type === "journal" ? "selected" : ""}>Journal</option>
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select name="status">
            <option value="">All statuses</option>
            <option value="posted" ${state.status === "posted" ? "selected" : ""}>Posted</option>
            <option value="reversed" ${state.status === "reversed" ? "selected" : ""}>Reversed</option>
            <option value="posting" ${state.status === "posting" ? "selected" : ""}>Posting</option>
          </select>
        </label>
        <label class="field">
          <span>Approval</span>
          <select name="approval_status">
            <option value="">All approvals</option>
            <option value="auto_posted" ${state.approval_status === "auto_posted" ? "selected" : ""}>Auto-posted</option>
            <option value="approved" ${state.approval_status === "approved" ? "selected" : ""}>Approved</option>
            <option value="rejected" ${state.approval_status === "rejected" ? "selected" : ""}>Rejected</option>
            <option value="pending_approval" ${state.approval_status === "pending_approval" ? "selected" : ""}>Pending approval</option>
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-list-filter" data-list-kind="vouchers">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-list-filter" data-list-kind="vouchers">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="vouchers" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="vouchers" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

function renderVoucherApprovalQueuePanel(items) {
  const rows = Array.isArray(items) ? items : [];
  const openItems = rows.filter((row) => ["pending_approval", "rejected"].includes(row.approval_status || "not_submitted"));
  const rejectedCount = openItems.filter((row) => row.approval_status === "rejected").length;
  const pendingCount = openItems.filter((row) => row.approval_status === "pending_approval").length;

  if (openItems.length === 0) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h5>Voucher review queue</h5>
            <p>No voucher reviews are pending in the current tenant context.</p>
          </div>
          <button class="secondary" type="button" data-business-action="voucher-queue-refresh">Refresh</button>
        </div>
      </div>
    `;
  }

  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h5>Voucher review queue</h5>
          <p>${escapeHtml(String(openItems.length))} voucher(s) still need explicit review visibility.</p>
        </div>
        <button class="secondary" type="button" data-business-action="voucher-queue-refresh">Refresh</button>
      </div>
      <div class="stats-grid">
        <div class="stat-card"><span>Open items</span><strong>${escapeHtml(String(openItems.length))}</strong></div>
        <div class="stat-card"><span>Pending</span><strong>${escapeHtml(String(pendingCount))}</strong></div>
        <div class="stat-card"><span>Rejected</span><strong>${escapeHtml(String(rejectedCount))}</strong></div>
      </div>
      <div class="table-preview compact-table erp-table">
        <table>
          <thead>
            <tr>
              <th>Voucher</th>
              <th>Date</th>
              <th>Amount</th>
              <th>Approval</th>
            </tr>
          </thead>
          <tbody>
            ${openItems.slice(0, 10).map((row) => `
              <tr>
                <td>
                  <strong>${escapeHtml(row.document_number || row.document_id || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.document_type || "voucher")}</span>
                </td>
                <td>${escapeHtml(String(row.document_date || row.created_at || "").slice(0, 10))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount || 0))}</td>
                <td><span class="pill ${row.approval_status === "rejected" ? "warn" : ""}">${escapeHtml(row.approval_status || "not_submitted")}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}






// ========== Business Module: Typed Vouchers ==========

let lastBusinessVouchers = [];
let lastVoucherApprovalQueue = [];
let lastBusinessAccountsResult = null;
let lastModuleContext = null;
let voucherLineCounter = 0;
let lastBusinessDashboardStats = null;
let lastBusinessMisKpis = null;
let lastBusinessDataHealth = null;
let lastFinancialHealth = null;
let financialHealthLoadInFlight = false;
let businessDataHealthLoadInFlight = false;

const voucherLineState = [];

const MITRABOOKS_FALLBACK_ACCOUNTS = [
  { account_id: 11001, account_code: "11001", account_name: "Cash in Hand", account_type: "asset" },
  { account_id: 11010, account_code: "11010", account_name: "Bank Account", account_type: "asset" },
  { account_id: 12001, account_code: "12001", account_name: "Sundry Debtors", account_type: "asset" },
  { account_id: 13002, account_code: "13002", account_name: "Advance to Suppliers", account_type: "asset" },
  { account_id: 21001, account_code: "21001", account_name: "Sundry Creditors", account_type: "liability" },
  { account_id: 24001, account_code: "24001", account_name: "Advance from Customers", account_type: "liability" },
  { account_id: 41001, account_code: "41001", account_name: "Sales", account_type: "income" },
  { account_id: 41002, account_code: "41002", account_name: "Service Income", account_type: "income" },
  { account_id: 53004, account_code: "53004", account_name: "Office Expense", account_type: "expense" },
  { account_id: 54001, account_code: "54001", account_name: "Bank Charges", account_type: "expense" },
];


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT HELPERS + DATA HEALTH
// NOTE  : normalizeBusinessAccount, businessAccountsForSelection, renderBusinessDataHealthPanel
// ══════════════════════════════════════════════════════════════════════

function normalizeBusinessAccount(acc) {
  const id = acc.account_id
    ?? acc.id
    ?? acc.accountId
    ?? acc.accountID
    ?? acc.ledger_id
    ?? acc.ledgerId
    ?? acc._id
    ?? acc.account_code
    ?? acc.code
    ?? "";
  const code = acc.account_code
    ?? acc.code
    ?? acc.accountCode
    ?? acc.ledger_code
    ?? acc.ledgerCode
    ?? acc.gl_code
    ?? acc.glCode
    ?? acc.number
    ?? acc.account_number
    ?? id
    ?? "";
  const name = acc.account_name
    ?? acc.name
    ?? acc.accountName
    ?? acc.ledger_name
    ?? acc.ledgerName
    ?? acc.title
    ?? "";
  return {
    id: String(id),
    code: String(code),
    name: String(name),
  };
}

function businessAccountLabel(account) {
  return `${account.code}${account.name ? " - " + account.name : ""}`.trim();
}

function businessAccountsForSelection() {
  const loaded = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [];
  const source = loaded.length > 0 ? loaded : MITRABOOKS_FALLBACK_ACCOUNTS;
  return source
    .map(normalizeBusinessAccount)
    .filter((acc) => acc.id && (acc.code || acc.name));
}

function hasLoadedBusinessAccounts() {
  return Array.isArray(lastBusinessAccounts) && lastBusinessAccounts.length > 0;
}

function findBusinessAccountById(accountId) {
  return businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId)) || null;
}

function accountIdForVoucherPayload(account) {
  if (!account || !hasLoadedBusinessAccounts()) return null;
  const parsed = Number(account.id);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function populateVoucherAccountSelect(select, selectedId = "") {
  if (!select) return;
  const accounts = businessAccountsForSelection();
  select.innerHTML = `<option value="">Select account code</option>`;
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = acc.id;
    option.textContent = businessAccountLabel(acc);
    if (String(selectedId) === acc.id) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function populateAccountPickerSelect(fieldId, accounts, selectedId = "") {
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  if (!select) return;
  const rows = Array.isArray(accounts) && accounts.length > 0 ? accounts : businessAccountsForSelection();
  const currentValue = selectedId || select.value || "";
  select.innerHTML = `<option value="">${rows.length === 0 ? "No matching account code" : "Select account code"}</option>`;
  rows.forEach((account) => {
    const normalized = normalizeBusinessAccount(account);
    const option = document.createElement("option");
    option.value = normalized.id;
    option.textContent = businessAccountLabel(normalized);
    if (String(currentValue) === String(normalized.id)) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function refreshVoucherAccountDatalist() {
  const datalist = document.getElementById("business-voucher-account-options");
  if (!datalist) return;
  const accounts = businessAccountsForSelection();
  datalist.innerHTML = "";
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = businessAccountLabel(acc);
    datalist.appendChild(option);
  });
}

function updateVoucherAccountsStatus() {
  const status = document.getElementById("business-voucher-accounts-status");
  if (!status) return;
  const count = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;
  status.textContent = "";
  if (count <= 0) {
    status.textContent = "No tenant chart loaded. Showing default MitraBooks account codes until the chart of accounts API returns rows.";
    return;
  }
  const message = document.createElement("span");
  message.textContent = `${count} account(s) loaded. Examples: `;
  status.appendChild(message);
  const preview = document.createElement("strong");
  preview.textContent = lastBusinessAccounts
    .slice(0, 3)
    .map((acc) => businessAccountLabel(normalizeBusinessAccount(acc)))
    .filter(Boolean)
    .join(" | ");
  status.appendChild(preview);
}

function refreshVoucherAccountSelects() {
  refreshVoucherAccountDatalist();
  updateVoucherAccountsStatus();
  document.querySelectorAll(".voucher-account-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
  document.querySelectorAll(".account-picker-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
}

function accountRowsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.accounts)) return payload.accounts;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.rows)) return payload.rows;
  if (Array.isArray(payload?.result)) return payload.result;
  if (Array.isArray(payload?.data?.items)) return payload.data.items;
  if (Array.isArray(payload?.data?.accounts)) return payload.data.accounts;
  if (Array.isArray(payload?.data?.rows)) return payload.data.rows;
  if (Array.isArray(payload?.result?.items)) return payload.result.items;
  if (Array.isArray(payload?.result?.accounts)) return payload.result.accounts;
  if (Array.isArray(payload?.payload?.items)) return payload.payload.items;
  if (Array.isArray(payload?.payload?.accounts)) return payload.payload.accounts;
  return [];
}

function isBusinessModuleEnabled(context) {
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return modules.some((module) => {
    const key = typeof module === "string" ? module : module?.module_key;
    return key === "business";
  });
}

function enabledModuleKeys(context = lastModuleContext) {
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return new Set(modules
    .map((module) => typeof module === "string" ? module : module?.module_key)
    .map((key) => String(key || "").trim().toLowerCase())
    .filter(Boolean));
}

function isPlatformOwnerContext(context = lastModuleContext) {
  const tenantId = String(context?.tenant_id || "").trim().toLowerCase();
  const role = String(context?.role || context?.user_role || "").trim().toLowerCase();
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return context?.is_platform_owner === true
    || role === "super_admin"
    || tenantId === "platform"
    || organizationType === "PLATFORM";
}

function isBusinessTenantContext(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return organizationType === "BUSINESS" && !isPlatformOwnerContext(context) && isBusinessModuleEnabled(context);
}

function normalizedAccountRows(rows = lastBusinessAccounts) {
  return Array.isArray(rows) ? rows.map((account) => {
    const normalized = normalizeBusinessAccount(account);
    return {
      ...normalized,
      type: String(account.account_type ?? account.type ?? "").toLowerCase(),
      nameKey: normalized.name.toLowerCase(),
    };
  }).filter((account) => account.id || account.code || account.name) : [];
}

function hasBusinessAccount(matchNames, matchTypes = []) {
  const names = matchNames.map((name) => name.toLowerCase());
  const types = matchTypes.map((type) => type.toLowerCase());
  return normalizedAccountRows().some((account) => {
    const nameMatch = names.some((name) => account.nameKey === name || account.nameKey.includes(name));
    const typeMatch = types.length === 0 || types.includes(account.type);
    return nameMatch && typeMatch;
  });
}

function countPartiesMissingGstin(rows = lastBusinessParties) {
  if (!Array.isArray(rows) || rows.length === 0) return 0;
  return rows.filter((row) => !String(row.gstin || "").trim()).length;
}

function dataHealthItem(label, ok, copy) {
  return `
    <li class="${ok ? "ok" : "warn"}">
      <span>${escapeHtml(label)}</span>
      <strong>${ok ? "Ready" : "Needs attention"}</strong>
      <small>${escapeHtml(copy)}</small>
    </li>
  `;
}

function dataHealthAction(priority, title, detail, actionText) {
  return `
    <li>
      <span>${escapeHtml(priority)}</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(detail)}</small>
      <em>${escapeHtml(actionText)}</em>
    </li>
  `;
}

function renderBusinessDataHealthIssueList(dataHealth) {
  const issues = Array.isArray(dataHealth?.issues) ? dataHealth.issues : [];
  if (issues.length === 0) return "";
  return `
    <div class="erp-health-actions data-health-remediation">
      <div>
        <h5>Remediation Queue</h5>
        <p>Source-backed issues with direct links to the workspace where the record can be reviewed.</p>
      </div>
      <ol>
        ${issues.slice(0, 8).map((issue) => {
          const workspace = issue.workspace || "overview";
          return `
            <li data-data-health-issue="${escapeHtml(issue.issue_id || "")}">
              <span>${escapeHtml(issue.severity || "issue")}</span>
              <strong>${escapeHtml(issue.title || "Data-health issue")}</strong>
              <small>${escapeHtml(issue.entity_label || issue.description || "Affected record")}</small>
              <em>${escapeHtml(issue.action || "Review the affected record.")}</em>
              <button
                class="secondary"
                type="button"
                data-business-action="workspace-view"
                data-workspace-view="${escapeHtml(workspace)}"
                data-data-health-rule="${escapeHtml(issue.rule_key || "")}"
              >${escapeHtml(issue.action_label || "Open Workspace")}</button>
            </li>
          `;
        }).join("")}
      </ol>
    </div>
  `;
}

function renderBusinessDataHealthActions(state) {
  const actions = [];
  const backendRules = Array.isArray(lastBusinessDataHealth?.rules) ? lastBusinessDataHealth.rules : [];

  backendRules
    .filter((rule) => rule.status !== "pass")
    .slice(0, 5)
    .forEach((rule) => {
      actions.push(dataHealthAction(
        rule.severity || "Rule",
        rule.label || rule.key || "Data-health rule",
        rule.detail || `${rule.count || 0} issue(s) found.`,
        rule.action || "Review the affected records."
      ));
    });

  if (!state.isBusinessTenant || !state.hasBusinessModule) {
    actions.push(dataHealthAction(
      "Access",
      "Fix MitraBooks tenant context",
      "Business workspaces need organization_type=BUSINESS and the business module enabled.",
      "Review tenant setup before adding more business records."
    ));
  }
  if (!state.hasAccountingModule || !state.accountsLoaded) {
    actions.push(dataHealthAction(
      "Setup",
      "Load the chart of accounts",
      state.accountsBlocked ? `Accounts request returned HTTP ${state.accountsStatus}.` : "The voucher form needs tenant-owned cash, bank, revenue, and expense ledgers.",
      "Open Accounting and confirm the business chart exists."
    ));
  }
  if (state.accountsLoaded && !state.hasCashBank) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add cash or bank account",
      "Receipt, payment, and contra vouchers need an asset-side cash or bank ledger.",
      "Create or map Cash in Hand / Bank Account before payment workflows."
    ));
  }
  if (state.accountsLoaded && !state.hasRevenue) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add revenue account",
      "Sales and service postings need an income/revenue ledger before invoice workflows are enabled.",
      "Create or map Sales / Service Income."
    ));
  }
  if (state.accountsLoaded && !state.hasExpense) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add expense account",
      "Purchase and expense postings need an expense ledger before purchase workflows are enabled.",
      "Create or map Purchases / Office Expense / Rent Expense."
    ));
  }
  if (state.partiesLoaded && state.partiesMissingGstin > 0) {
    actions.push(dataHealthAction(
      "Parties",
      "Complete party GSTINs",
      `${state.partiesMissingGstin} visible party record(s) are missing GSTIN.`,
      "Open Parties and update GSTIN where the party is registered."
    ));
  }
  if (state.partiesBlocked) {
    actions.push(dataHealthAction(
      "Parties",
      "Reload party sample",
      "The dashboard could not read the visible party sample used for GSTIN checks.",
      "Open Parties after confirming the business module is enabled."
    ));
  }
  if (!state.drilldownReady) {
    actions.push(dataHealthAction(
      "Reports",
      "Verify voucher drill-down",
      "Accounting report drill-down must load before reports can be trusted for business review.",
      "Open Accounting and retry after posting a balanced voucher."
    ));
  }

  if (actions.length === 0) {
    actions.push(dataHealthAction(
      "Ready",
      "Core accounting data is ready",
      "Tenant context, modules, chart of accounts, party GSTIN sample, and drill-down are available.",
      "Continue with parties and balanced vouchers; keep GST/inventory depth deferred."
    ));
  }

  return `
    <div class="erp-health-actions">
      <div>
        <h5>Action Queue</h5>
        <p>Concrete next fixes before expanding into sales, purchases, GST, or inventory.</p>
      </div>
      <ol>${actions.join("")}</ol>
    </div>
  `;
}

function getBusinessHealthState() {
  const modules = enabledModuleKeys();
  const organizationType = String(lastModuleContext?.organization_type || "unknown").toUpperCase();
  const tenantId = lastModuleContext?.tenant_id || "not loaded";
  const accountsLoaded = Array.isArray(lastBusinessAccounts) && lastBusinessAccounts.length > 0;
  const accountsBlocked = lastBusinessAccountsResult && !lastBusinessAccountsResult.ok;
  const accountsStatus = lastBusinessAccountsResult?.status || "unknown";
  const partiesLoaded = Array.isArray(lastBusinessParties) && lastBusinessParties.length > 0;
  const partiesBlocked = lastBusinessPartiesResult && !lastBusinessPartiesResult.ok;
  const partiesMissingGstin = countPartiesMissingGstin();
  const partiesGstinReady = !partiesBlocked && (!partiesLoaded || partiesMissingGstin === 0);
  const partiesGstinCopy = partiesBlocked
    ? `Parties request returned HTTP ${lastBusinessPartiesResult.status}.`
    : partiesLoaded
      ? `${partiesMissingGstin} visible party record(s) missing GSTIN.`
      : "No visible parties yet; GSTIN checks start after party creation.";
  const drilldownReady = lastAccountingDrilldown && lastAccountingDrilldown.ok !== false;
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const healthState = {
    isBusinessTenant: isBusinessTenantContext(),
    hasBusinessModule: modules.has("business"),
    hasAccountingModule: modules.has("accounting"),
    accountsLoaded,
    accountsBlocked,
    accountsStatus,
    hasCashBank: hasBusinessAccount(["Cash in Hand", "Bank Account"], ["asset"]),
    hasRevenue: hasBusinessAccount(["Sales", "Service Income"], ["income", "revenue"]),
    hasExpense: hasBusinessAccount(["Purchases", "Office Expense", "Rent Expense"], ["expense"]),
    partiesLoaded,
    partiesBlocked,
    partiesMissingGstin,
    partiesGstinReady,
    drilldownReady,
  };

  return {
    healthState,
    organizationType,
    tenantId,
    partiesGstinCopy,
    voucherCount,
  };
}

function renderBusinessDataHealthPanel() {
  const { healthState, organizationType, tenantId, partiesGstinCopy, voucherCount } = getBusinessHealthState();
  if (hasTrustedSession() && !lastBusinessDataHealth && !businessDataHealthLoadInFlight) {
    setTimeout(() => { loadBusinessDataHealth(); }, 0);
  }
  const dataHealth = lastBusinessDataHealth;
  const score = Number(dataHealth?.score ?? 0);
  const scoreLabel = dataHealth ? `${score}/100` : "Loading";
  const gradeLabel = dataHealth?.grade ? `Grade ${dataHealth.grade}` : "backend score";
  const backendRules = Array.isArray(dataHealth?.rules) ? dataHealth.rules : [];

  const checks = [
    dataHealthItem("Data Health Score", !!dataHealth && score >= 75, `${scoreLabel}; ${gradeLabel}`),
    dataHealthItem("Business tenant context", healthState.isBusinessTenant, `organization_type=${organizationType}; tenant=${tenantId}`),
    dataHealthItem("Business module enabled", healthState.hasBusinessModule, "Required before parties and vouchers can return tenant data."),
    dataHealthItem("Accounting module enabled", healthState.hasAccountingModule, "Required for chart of accounts and drill-down reports."),
    dataHealthItem("Chart of accounts loaded", healthState.accountsLoaded, healthState.accountsBlocked ? `Accounts request returned HTTP ${lastBusinessAccountsResult.status}.` : `${lastBusinessAccounts.length} account(s) available.`),
    dataHealthItem("Cash and bank accounts", healthState.hasCashBank, "Required for receipt, payment, and contra voucher posting."),
    dataHealthItem("Revenue / income accounts", healthState.hasRevenue, "Required before sales or service income postings are introduced."),
    dataHealthItem("Expense accounts", healthState.hasExpense, "Required for purchase and expense postings."),
    dataHealthItem("Party GSTIN sample", healthState.partiesGstinReady, partiesGstinCopy),
    dataHealthItem("Voucher drill-down", healthState.drilldownReady, `Current period shows ${voucherCount} posted voucher(s).`),
  ];
  backendRules.forEach((rule) => {
    checks.push(dataHealthItem(
      rule.label || rule.key || "Data-health rule",
      rule.status === "pass",
      `${rule.count || 0} issue(s); impact ${rule.score_impact || 0}`
    ));
  });

  return `
    <section class="erp-health-panel" aria-label="MitraBooks data health">
      <div class="preview-heading compact">
        <div>
          <h4>Data Health</h4>
          <p>${escapeHtml(dataHealth?.summary || "Tenant, module, chart, and drill-down readiness for the current MitraBooks context.")}</p>
        </div>
        <span class="pill ${dataHealth?.status === "ready" ? "ok" : "warn"}">${escapeHtml(scoreLabel)}</span>
      </div>
      <ul class="erp-health-list">${checks.join("")}</ul>
      ${renderBusinessDataHealthIssueList(dataHealth)}
      ${renderBusinessDataHealthActions(healthState)}
    </section>
  `;
}

async function loadBusinessPartiesForHealth() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/parties?offset=0&limit=20", { method: "GET" });
  lastBusinessPartiesResult = result;
  if (result.ok) {
    lastBusinessParties = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
  }
  return result;
}

async function loadModuleContextForAccounts() {
  if (lastModuleContext) return lastModuleContext;
  const result = await loadModules("mitrabooks");
  if (result.ok) {
    lastModuleContext = result.payload;
  }
  return lastModuleContext;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHER FORM HELPERS
// NOTE  : renderVoucherLineItem, updateVoucherBalance, addVoucherLine, clearVoucherForm
// ══════════════════════════════════════════════════════════════════════

function syncVoucherAccountFromText(lineEl) {
  const input = lineEl?.querySelector(".voucher-account");
  const select = lineEl?.querySelector(".voucher-account-select");
  const query = String(input?.value || "").trim().toLowerCase();
  if (!query || !select) return;
  const match = (Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [])
    .map(normalizeBusinessAccount)
    .find((acc) => acc.code.toLowerCase().startsWith(query) || acc.name.toLowerCase().includes(query));
  if (match?.id) {
    select.value = match.id;
  }
}

function renderVoucherLineItem(lineId, voucherType) {
  const accountSelector = renderAccountSelectorComponent(`voucher-account-${lineId}`);

  return `
    <div class="voucher-line" data-line-id="${escapeHtml(lineId)}">
      <div class="voucher-line-grid">
        <div class="voucher-account-field">
          <label>Account</label>
          ${accountSelector}
        </div>
        <div class="voucher-amount-field">
          <label>Debit (₹)</label>
          <input
            class="voucher-debit"
            type="number"
            placeholder="0.00"
            min="0"
            step="0.01"
            data-line-id="${escapeHtml(lineId)}"
          >
        </div>
        <div class="voucher-amount-field">
          <label>Credit (₹)</label>
          <input
            class="voucher-credit"
            type="number"
            placeholder="0.00"
            min="0"
            step="0.01"
            data-line-id="${escapeHtml(lineId)}"
          >
        </div>
        <div class="voucher-action-field">
          <button
            class="secondary"
            type="button"
            data-business-action="remove-voucher-line"
            data-line-id="${escapeHtml(lineId)}"
          >Remove</button>
        </div>
      </div>
    </div>
  `;
}

function updateVoucherBalance() {
  let totalDebit = 0;
  let totalCredit = 0;

  document.querySelectorAll(".voucher-debit").forEach((input) => {
    totalDebit += Number(input.value) || 0;
  });

  document.querySelectorAll(".voucher-credit").forEach((input) => {
    totalCredit += Number(input.value) || 0;
  });

  const simpleAmountInput = document.getElementById("business-voucher-amount");
  const isSimplePartyVoucher = simpleAmountInput && !document.querySelector(".voucher-debit, .voucher-credit");
  if (isSimplePartyVoucher) {
    const amount = Number(simpleAmountInput.value) || 0;
    totalDebit = amount;
    totalCredit = amount;
  }

  const hasAmount = totalDebit > 0 || totalCredit > 0;
  const isBalanced = hasAmount && Math.abs(totalDebit - totalCredit) < 0.01;
  const balanceEl = document.getElementById("business-voucher-balance");
  if (balanceEl) {
    balanceEl.className = isBalanced ? "voucher-balance-status balanced" : "voucher-balance-status imbalanced";
    balanceEl.innerHTML = `
      <span>Debit: ${formatCurrency(totalDebit)}</span>
      <span>Credit: ${formatCurrency(totalCredit)}</span>
      <strong>${isBalanced ? "Debit = Credit" : "Debit must equal Credit"}</strong>
    `;
  }

  const submitBtn = document.getElementById("business-voucher-submit");
  if (submitBtn) {
    submitBtn.disabled = !isBalanced;
  }
}

function updateVoucherBalanceState() {
  let totalDebit = 0;
  let totalCredit = 0;

  document.querySelectorAll(".voucher-debit").forEach((input) => {
    totalDebit += Number(input.value) || 0;
  });
  document.querySelectorAll(".voucher-credit").forEach((input) => {
    totalCredit += Number(input.value) || 0;
  });

  const hasAmount = totalDebit > 0 || totalCredit > 0;
  const isBalanced = hasAmount && Math.abs(totalDebit - totalCredit) < 0.01;
  const balanceEl = document.getElementById("business-voucher-balance");
  if (balanceEl) {
    balanceEl.className = isBalanced ? "voucher-balance-status balanced" : "voucher-balance-status imbalanced";
    balanceEl.innerHTML = `
      <span>Debit: ${formatCurrency(totalDebit)}</span>
      <span>Credit: ${formatCurrency(totalCredit)}</span>
      <strong>${isBalanced ? "Balanced" : "Imbalanced"}</strong>
    `;
  }

  const submitBtn = document.getElementById("business-voucher-submit");
  if (submitBtn) {
    submitBtn.disabled = !isBalanced;
  }
}

function addVoucherLine() {
  voucherLineCounter += 1;
  const lineId = `line-${voucherLineCounter}`;
  const container = document.getElementById("business-voucher-lines");
  if (!container) return;

  const lineHtml = renderVoucherLineItem(lineId);
  container.insertAdjacentHTML("beforeend", lineHtml);
  refreshVoucherAccountDatalist();
  updateVoucherAccountsStatus();

  const select = container.querySelector(`[data-line-id="${lineId}"].voucher-account-select`);
  populateVoucherAccountSelect(select);
  if (select) {
    select.addEventListener("change", () => {
      const selected = normalizeBusinessAccount(lastBusinessAccounts.find((acc) => String(acc.account_id ?? acc.id ?? "") === select.value) || {});
      const accountInput = container.querySelector(`[data-line-id="${lineId}"].voucher-account`);
      if (accountInput && selected.id) {
        accountInput.value = businessAccountLabel(selected);
      }
    });
  }

  const accountInput = container.querySelector(`[data-line-id="${lineId}"].voucher-account`);
  const debitInput = container.querySelector(`[data-line-id="${lineId}"].voucher-debit`);
  const creditInput = container.querySelector(`[data-line-id="${lineId}"].voucher-credit`);
  if (accountInput) accountInput.addEventListener("input", () => syncVoucherAccountFromText(accountInput.closest(".voucher-line")));
  if (debitInput) debitInput.addEventListener("input", updateVoucherBalanceState);
  if (creditInput) creditInput.addEventListener("input", updateVoucherBalanceState);
}

function removeVoucherLine(lineId) {
  const lineEl = Array.from(document.querySelectorAll(".voucher-line"))
    .find((candidate) => candidate.getAttribute("data-line-id") === lineId);
  if (lineEl) {
    lineEl.remove();
    updateVoucherBalanceState();
  }
}

function clearVoucherForm() {
  voucherLineCounter = 0;
  document.getElementById("business-voucher-date").valueAsDate = new Date();
  document.getElementById("business-voucher-reference").value = "";
  document.getElementById("business-voucher-narration").value = "";
  document.getElementById("business-voucher-lines").innerHTML = "";
  updateVoucherBalanceState();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT LOADING + FINANCIAL HEALTH LOADER
// API   : GET /api/v1/accounting/accounts  GET /api/v1/business/financial-health
// NOTE  : loadBusinessAccounts, loadFinancialHealth, loadBusinessDashboardStats
// ══════════════════════════════════════════════════════════════════════

async function loadBusinessAccounts() {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, "/api/v1/accounting/accounts", { method: "GET" });
  lastBusinessAccountsResult = result;

  if (result.ok) {
    lastBusinessAccounts = accountRowsFromPayload(result.payload);
    if (lastBusinessAccounts.length === 0) {
      const context = await loadModuleContextForAccounts();
      if (String(context?.organization_type || "").toUpperCase() !== "BUSINESS" || !isBusinessModuleEnabled(context)) {
        setLoginStatus(
          "warn",
          "MitraBooks business tenant required",
          `Current tenant is ${context?.organization_type || "unknown"} (${context?.tenant_id || "unknown"}). Sign in as ${DEFAULT_MITRABOOKS_LOGIN_EMAIL} for voucher posting.`
        );
      } else {
        setLoginStatus("warn", "No chart of accounts found", "Initialize the MitraBooks chart of accounts before posting vouchers.");
      }
    }
    refreshVoucherAccountSelects();
  } else {
    lastBusinessAccounts = [];
    setLoginStatus("danger", "Unable to load accounts", statusDetailText(result.payload?.detail) || "Check accounting access and try again.");
    updateVoucherAccountsStatus();
  }
}

// ========== Business Dashboard Data Loading ==========

/**
 * Load dashboard statistics from API
 * Fetches live KPI data: income, expenses, net position, GST, cash, receivables, payables
 */
async function loadBusinessDashboardStats() {
  if (!hasTrustedSession()) {
    return;
  }
  const appKey = "mitrabooks";
  businessDashboardLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/dashboard", { method: "GET" });
  } finally {
    businessDashboardLoadInFlight = false;
  }

  // A valid dashboard payload always carries the income block; guard against an
  // empty/partial body (e.g. a transient 0-byte response during a service-worker
  // swap) so it can't blank out good data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object" && result.payload.income;

  if (hasValidPayload) {
    lastBusinessDashboardStats = result.payload;
    // Re-render whenever we're in the MitraBooks experience; renderDashboardPreview
    // itself routes to the right view (overview vs other workspaces).
    if (currentExperience === "mitrabooks") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else if (!lastBusinessDashboardStats) {
    // Only surface "unavailable" when we have no prior good data — never clobber a
    // working dashboard with a transient failure.
    setLoginStatus(
      "warn",
      "Dashboard data unavailable",
      "Live dashboard figures could not be loaded; showing zeros until the ledger responds."
    );
  }

  renderJson(apiOutput, { dashboard: { ok: result.ok, hasData: !!lastBusinessDashboardStats } });
}

async function loadFinancialHealth() {
  const appKey = "mitrabooks";
  financialHealthLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/financial-health", { method: "GET" });
  } finally {
    financialHealthLoadInFlight = false;
  }

  // A valid payload always carries the kpis array; guard against an empty/partial
  // body so a transient failure can't blank out data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.kpis);

  if (hasValidPayload) {
    lastFinancialHealth = result.payload;
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "financial-health") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else if (!lastFinancialHealth) {
    setLoginStatus(
      "warn",
      "Financial Health unavailable",
      result.payload?.detail || "Live financial-health figures could not be loaded.",
    );
  }

  renderJson(apiOutput, { financialHealth: { ok: result.ok, hasData: !!lastFinancialHealth } });
}

async function loadBusinessMisKpis() {
  if (!hasTrustedSession()) {
    return;
  }
  const appKey = "mitrabooks";
  businessMisLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/mis/kpis", { method: "GET" });
  } finally {
    businessMisLoadInFlight = false;
  }

  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.monthly_sales_purchase_trend);

  if (hasValidPayload) {
    lastBusinessMisKpis = result.payload;
    if (currentExperience === "mitrabooks") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else if (!lastBusinessMisKpis) {
    setLoginStatus(
      "warn",
      "MIS KPIs unavailable",
      result.payload?.detail || "Source-backed MIS KPI contracts could not be loaded.",
    );
  }

  renderJson(apiOutput, { misKpis: { ok: result.ok, hasData: !!lastBusinessMisKpis } });
}

async function loadBusinessDataHealth() {
  if (!hasTrustedSession()) {
    return;
  }
  businessDataHealthLoadInFlight = true;
  let result;
  try {
    result = await apiRequest("mitrabooks", "/api/v1/business/data-health", { method: "GET" });
  } finally {
    businessDataHealthLoadInFlight = false;
  }

  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.rules);

  if (hasValidPayload) {
    lastBusinessDataHealth = result.payload;
    if (currentExperience === "mitrabooks") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else if (!lastBusinessDataHealth) {
    setLoginStatus(
      "warn",
      "Data Health unavailable",
      result.payload?.detail || "Source-backed data-health rules could not be loaded.",
    );
  }

  renderJson(apiOutput, { dataHealth: { ok: result.ok, hasData: !!lastBusinessDataHealth } });
}

// ========== Account Selector Component (Searchable) ==========

/**
 * Filter accounts by search query (min 3 chars)
 * Returns array of matching accounts with code and name
 */
function filterBusinessAccountsByQuery(query) {
  const q = String(query || "").trim().toLowerCase();

  // Min 3 characters to filter
  if (q.length < 3) {
    return [];
  }

  const matches = businessAccountsForSelection().filter((normalized) => {
    const code = normalized.code.toLowerCase();
    const name = normalized.name.toLowerCase();
    const type = String(normalized.account_type || normalized.type || "").toLowerCase();

    return (
      code.includes(q) ||
      name.includes(q) ||
      type.includes(q)
    );
  });

  // Return max 20 results
  return matches.slice(0, 20);
}

/**
 * Render account selector HTML (searchable input + suggestions)
 * @param {string} fieldId - Unique ID for this selector (e.g., "debit-account", "credit-account")
 * @param {number} selectedAccountId - Currently selected account ID (optional)
 * @returns {string} HTML for the account selector component
 */

// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT SELECTOR COMPONENT
// NOTE  : renderAccountSelectorComponent, selectBusinessAccount — inline searchable dropdown
// ══════════════════════════════════════════════════════════════════════

function renderAccountSelectorComponent(fieldId, selectedAccountId = null) {
  const accounts = businessAccountsForSelection();
  const selectedAccount = accounts.find((acc) => String(acc.id) === String(selectedAccountId));
  const usingFallbackAccounts = !Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0;

  const displayText = selectedAccount
    ? `${selectedAccount.code} - ${selectedAccount.name}`
    : "";

  return `
    <div class="account-selector-component" data-field-id="${escapeHtml(fieldId)}">
      <span class="account-selector-caption">Account code dropdown</span>
      <div class="account-input-wrapper">
        <select
          class="account-picker-select"
          data-field-id="${escapeHtml(fieldId)}"
          aria-label="Select account"
        >
          <option value="">Select account code</option>
          ${accounts.map((account) => `
            <option value="${escapeHtml(account.id)}" ${String(account.id) === String(selectedAccountId || "") ? "selected" : ""}>
              ${escapeHtml(`${account.code} - ${account.name}`)}
            </option>
          `).join("")}
        </select>
        <input
          type="text"
          class="account-search-input"
          data-field-id="${escapeHtml(fieldId)}"
          placeholder="Type 3+ characters to filter account codes"
          value="${escapeHtml(displayText)}"
          autocomplete="off"
        >
        <input
          type="hidden"
          class="account-id-input"
          data-field-id="${escapeHtml(fieldId)}"
          value="${escapeHtml(selectedAccountId || "")}"
        >
      </div>
      <ul class="account-suggestions" data-field-id="${escapeHtml(fieldId)}" hidden>
        <!-- Populated on input -->
      </ul>
      ${usingFallbackAccounts ? `<p class="account-selector-note">Using default account codes. Load tenant chart of accounts to replace these defaults.</p>` : ""}
    </div>
  `;
}

/**
 * Update account selector suggestions as user types
 */
function updateAccountSuggestions(fieldId) {
  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (!input || !suggestionsList) return;

  const query = input.value.trim();
  const matches = filterBusinessAccountsByQuery(query);

  if (query.length < 3) {
    populateAccountPickerSelect(fieldId, businessAccountsForSelection());
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
    return;
  }

  populateAccountPickerSelect(fieldId, matches);

  if (matches.length === 0) {
    suggestionsList.hidden = false;
    suggestionsList.innerHTML = `<li class="account-suggestion-empty">No matching account code</li>`;
    return;
  }

  suggestionsList.innerHTML = matches
    .map((acc) => {
      const normalized = normalizeBusinessAccount(acc);
      const displayText = `${normalized.code} - ${normalized.name}`;
      return `
        <li
          class="account-suggestion-item"
          data-account-id="${escapeHtml(normalized.id)}"
          data-field-id="${escapeHtml(fieldId)}"
          title="${escapeHtml(displayText)}"
        >
          <strong>${escapeHtml(normalized.code)}</strong>
          <span>${escapeHtml(normalized.name)}</span>
        </li>
      `;
    })
    .join("");

  suggestionsList.hidden = false;
}

/**
 * Select an account from suggestions
 */
function selectAccountFromSuggestion(suggestionElement) {
  const fieldId = suggestionElement.getAttribute("data-field-id");
  const accountId = suggestionElement.getAttribute("data-account-id");

  selectBusinessAccount(fieldId, accountId);
}

function selectBusinessAccount(fieldId, accountId) {
  const account = businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId));
  if (!account) return;

  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const idInput = document.querySelector(`.account-id-input[data-field-id="${fieldId}"]`);
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (input) {
    input.value = `${account.code} - ${account.name}`;
  }
  if (idInput) {
    idInput.value = account.id;
  }
  if (select) {
    select.value = account.id;
  }
  if (suggestionsList) {
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
  }

  // Trigger balance check if this is a voucher form
  updateVoucherBalance();
}

/**
 * Close all account suggestions dropdowns
 */
function closeAllAccountSuggestions() {
  document.querySelectorAll(".account-suggestions").forEach((list) => {
    list.hidden = true;
  });
}

// ========== Account Selector Event Handlers ==========

document.addEventListener("input", (event) => {
  // Payment-allocation amount inputs: update state silently (no re-render) so
  // the field keeps focus while typing. The total is recomputed on next render.
  const allocLine = event.target.closest("[data-alloc-line]");
  if (allocLine) {
    setAllocationLineAmount(allocLine.getAttribute("data-alloc-line"), allocLine.value);
    return;
  }

  // Handle account selector input
  const accountInput = event.target.closest(".account-search-input");
  if (accountInput) {
    const fieldId = accountInput.getAttribute("data-field-id");
    if (fieldId) {
      updateAccountSuggestions(fieldId);
    }
    return;
  }

  if (event.target?.id === "business-voucher-amount") {
    updateVoucherBalance();
    return;
  }

  // Handle debit/credit input changes - update balance
  const amountInput = event.target.closest(".voucher-debit, .voucher-credit");
  if (amountInput) {
    updateVoucherBalance();
  }
});

document.addEventListener("change", (event) => {
  if (event.target && event.target.id === "business-voucher-party") {
    loadVoucherPartyOutstanding(event.target.value, event.target.getAttribute("data-voucher-type") || "");
    return;
  }
  const accountSelect = event.target.closest(".account-picker-select");
  if (!accountSelect) {
    return;
  }
  const fieldId = accountSelect.getAttribute("data-field-id");
  if (fieldId && accountSelect.value) {
    selectBusinessAccount(fieldId, accountSelect.value);
  }
});


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS — creation helpers (party / contra / journal)
// API   : POST /api/v1/business/vouchers/...
// NOTE  : createSimplePartyVoucher, createContraVoucher, createJournalVoucher
// ══════════════════════════════════════════════════════════════════════

async function loadVoucherPartyOutstanding(partyId, voucherType) {
  const box = document.getElementById("business-voucher-outstanding");
  if (!box) return;
  if (!partyId) { box.textContent = ""; return; }
  box.textContent = "Loading outstanding…";
  const result = await apiRequest("mitrabooks", `/api/v1/business/parties/${encodeURIComponent(partyId)}/outstanding`, { method: "GET" });
  if (!result.ok) { box.textContent = ""; return; }
  const recv = Number(result.payload?.receivable || 0);
  const pay = Number(result.payload?.payable || 0);
  // Emphasise the side relevant to the voucher: receipt → receivable, payment → payable.
  const primary = voucherType === "payment"
    ? `Outstanding payable: <strong>${escapeHtml(formatCurrency(pay))}</strong>`
    : `Outstanding receivable: <strong>${escapeHtml(formatCurrency(recv))}</strong>`;
  const secondary = voucherType === "payment"
    ? `receivable ${escapeHtml(formatCurrency(recv))}`
    : `payable ${escapeHtml(formatCurrency(pay))}`;
  box.innerHTML = `${primary} <span class="muted">(${secondary})</span>`;
}

document.addEventListener("click", (event) => {
  const suggestion = event.target.closest(".account-suggestion-item");
  if (suggestion) {
    selectAccountFromSuggestion(suggestion);
    return;
  }

  // Close suggestions if clicking outside
  const component = event.target.closest(".account-selector-component");
  if (!component) {
    closeAllAccountSuggestions();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeAllAccountSuggestions();
  }
});

// ========== Voucher Form Integration ==========

/**
 * Create voucher by type - handles Payment, Receipt, Contra, Journal
 */
async function createBusinessVoucherByType(voucherType, date) {
  const appKey = "mitrabooks";

  try {
    if (voucherType === "payment" || voucherType === "receipt") {
      await createSimplePartyVoucher(appKey, voucherType, date);
    } else if (voucherType === "contra") {
      await createContraVoucher(appKey, date);
    } else if (voucherType === "journal") {
      await createJournalVoucher(appKey, date);
    } else {
      setLoginStatus("warn", "Unknown voucher type", `Voucher type '${voucherType}' is not supported.`);
    }
  } catch (error) {
    setLoginStatus("danger", "Voucher creation failed", error.message || "An unexpected error occurred.");
  }
}

/**
 * Create Payment or Receipt voucher (simple: one party, one bank/cash account)
 */
async function createSimplePartyVoucher(appKey, voucherType, date) {
  const partyId = document.getElementById("business-voucher-party")?.value || "";
  const amount = document.getElementById("business-voucher-amount")?.value || "0";
  const debitAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-debit-account']");
  const creditAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-credit-account']");
  const debitAccountId = debitAccountIdInput?.value || "";
  const creditAccountId = creditAccountIdInput?.value || "";
  const debitAccount = findBusinessAccountById(debitAccountId);
  const creditAccount = findBusinessAccountById(creditAccountId);
  const description = document.getElementById("business-voucher-description")?.value || "";
  const reference = document.getElementById("business-voucher-reference")?.value || "";

  if (!partyId) {
    setLoginStatus("warn", "Party required", "Select a party for this voucher.");
    return;
  }

  if (!debitAccount || !creditAccount) {
    setLoginStatus("warn", "Debit and credit accounts required", "Select both sides of the voucher before posting.");
    return;
  }

  if (String(debitAccount.id) === String(creditAccount.id) || debitAccount.code === creditAccount.code) {
    setLoginStatus("warn", "Different accounts required", "Debit and credit accounts cannot be the same ledger account.");
    return;
  }

  const amountVal = Number(amount);
  if (amountVal <= 0) {
    setLoginStatus("warn", "Invalid amount", "Amount must be greater than zero.");
    return;
  }

  const payload = {
    voucher_type: voucherType,
    entry_date: date,
    amount: amountVal.toFixed(2),
    debit_account_id: accountIdForVoucherPayload(debitAccount),
    credit_account_id: accountIdForVoucherPayload(creditAccount),
    debit_account_code: debitAccount.code,
    credit_account_code: creditAccount.code,
    description: description || `${voucherType} voucher`,
    reference: reference || null,
    party_id: partyId,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", `${voucherType.toUpperCase()} voucher sent for approval.`);
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

/**
 * Create Contra voucher (bank to bank transfer)
 */
async function createContraVoucher(appKey, date) {
  const fromAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-from-account']");
  const toAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-to-account']");
  const fromAccountId = fromAccountIdInput?.value || "";
  const toAccountId = toAccountIdInput?.value || "";
  const fromAccount = findBusinessAccountById(fromAccountId);
  const toAccount = findBusinessAccountById(toAccountId);
  const amount = document.getElementById("business-voucher-amount")?.value || "0";
  const description = document.getElementById("business-voucher-description")?.value || "Bank transfer";

  if (!fromAccount || !toAccount) {
    setLoginStatus("warn", "Accounts required", "Select both From and To accounts.");
    return;
  }

  if (String(fromAccount.id) === String(toAccount.id) || fromAccount.code === toAccount.code) {
    setLoginStatus("warn", "Same account", "From and To accounts must be different.");
    return;
  }

  const amountVal = Number(amount);
  if (amountVal <= 0) {
    setLoginStatus("warn", "Invalid amount", "Amount must be greater than zero.");
    return;
  }

  const payload = {
    voucher_type: "contra",
    entry_date: date,
    amount: amountVal.toFixed(2),
    debit_account_id: accountIdForVoucherPayload(toAccount),
    credit_account_id: accountIdForVoucherPayload(fromAccount),
    debit_account_code: toAccount.code,
    credit_account_code: fromAccount.code,
    description: description,
    reference: null,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-contra-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", "Contra voucher sent for approval.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

/**
 * Create Journal voucher (custom debit/credit lines)
 */
async function createJournalVoucher(appKey, date) {
  const description = document.getElementById("business-voucher-description")?.value || "";

  const debitLines = [];
  const creditLines = [];
  document.querySelectorAll(".voucher-line").forEach((lineEl) => {
    const accountIdInput = lineEl.querySelector(".account-id-input");
    const debitInput = lineEl.querySelector(".voucher-debit");
    const creditInput = lineEl.querySelector(".voucher-credit");

    const accountId = accountIdInput?.value || "";
    const account = findBusinessAccountById(accountId);
    const debit = Number(debitInput?.value) || 0;
    const credit = Number(creditInput?.value) || 0;

    if (account && (debit > 0 || credit > 0)) {
      const lineAccount = {
        account_id: accountIdForVoucherPayload(account),
        account_code: account.code,
        amount: "",
      };
      if (debit > 0) debitLines.push({ ...lineAccount, amount: debit.toFixed(2) });
      if (credit > 0) creditLines.push({ ...lineAccount, amount: credit.toFixed(2) });
    }
  });

  if (debitLines.length !== 1 || creditLines.length !== 1) {
    setLoginStatus("warn", "One debit and one credit required", "Phase 1 supports one debit and one credit account per entry.");
    return;
  }

  const debitTotal = Number(debitLines[0].amount);
  const creditTotal = Number(creditLines[0].amount);
  if (Math.abs(debitTotal - creditTotal) >= 0.01) {
    setLoginStatus("warn", "Voucher is not balanced", "Debit amount must equal credit amount.");
    return;
  }

  const payload = {
    voucher_type: "journal",
    entry_date: date,
    amount: debitTotal.toFixed(2),
    debit_account_id: debitLines[0].account_id,
    credit_account_id: creditLines[0].account_id,
    debit_account_code: debitLines[0].account_code,
    credit_account_code: creditLines[0].account_code,
    description: description || "Journal entry",
    reference: null,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-journal-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", "Journal entry sent for approval.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

async function createBusinessVoucher(voucherData) {
  const appKey = "mitrabooks";

  const debitLines = [];
  const creditLines = [];
  document.querySelectorAll(".voucher-line").forEach((lineEl) => {
    // Read account ID from hidden input in account selector component
    const accountIdInput = lineEl.querySelector(".account-id-input");
    const debitInput = lineEl.querySelector(".voucher-debit");
    const creditInput = lineEl.querySelector(".voucher-credit");

    const accountId = accountIdInput?.value || "";
    const debit = Number(debitInput?.value) || 0;
    const credit = Number(creditInput?.value) || 0;

    if (accountId && (debit > 0 || credit > 0)) {
      if (debit > 0) debitLines.push({ account_id: Number(accountId), amount: debit.toFixed(2) });
      if (credit > 0) creditLines.push({ account_id: Number(accountId), amount: credit.toFixed(2) });
    }
  });

  if (debitLines.length !== 1 || creditLines.length !== 1) {
    setLoginStatus("warn", "One debit and one credit required", "Phase 1 voucher posting supports one debit account and one credit account.");
    return;
  }
  const debitTotal = debitLines[0].amount;
  const creditTotal = creditLines[0].amount;
  if (Math.abs(debitTotal - creditTotal) >= 0.01) {
    setLoginStatus("warn", "Voucher is not balanced", "Debit amount must equal credit amount.");
    return;
  }

  const payload = {
    voucher_type: "journal",
    entry_date: voucherData.date,
    amount: debitTotal.toFixed(2),
    debit_account_id: debitLines[0].account_id,
    credit_account_id: creditLines[0].account_id,
    description: voucherData.narration || voucherData.reference || "Business voucher",
    reference: voucherData.reference || null,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", `Journal entry ${result.payload?.voucher_number || "created"} sent for approval.`);
    document.getElementById("business-voucher-create-dialog")?.close();
    clearVoucherForm();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    // Force refresh of current workspace
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS — CRUD + list
// API   : GET /api/v1/business/vouchers  POST /api/v1/business/vouchers/{type}
// NOTE  : loadBusinessVouchers, reverseBusinessVoucher, openBusinessCreateVoucherDialog
// ══════════════════════════════════════════════════════════════════════

async function loadBusinessVouchers(filters = {}) {
  const appKey = "mitrabooks";
  const params = new URLSearchParams();
  const state = businessListState.vouchers;
  const merged = {
    offset: state.offset || 0,
    limit: 20,
    voucher_type: state.voucher_type || "",
    status: state.status || "",
    approval_status: state.approval_status || "",
    ...filters,
  };
  params.append("offset", merged.offset);
  params.append("limit", merged.limit);
  if (merged.voucher_type) params.append("voucher_type", merged.voucher_type);
  if (merged.status) params.append("status", merged.status);
  if (merged.approval_status) params.append("approval_status", merged.approval_status);

  const queryString = params.toString();
  const url = `/api/v1/business/vouchers${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  if (result.ok) {
    lastBusinessVouchers = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessVouchers = [];
    setLoginStatus("danger", "Unable to load vouchers", statusDetailText(result.payload?.detail) || `Voucher list request failed with HTTP ${result.status}.`);
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  }
  renderJson(apiOutput, { vouchers: { ok: result.ok, status: result.status, count: lastBusinessVouchers.length, detail: result.payload?.detail || null } });
}

async function loadVoucherApprovalQueue(includeReviewed = true, options = {}) {
  const appKey = "mitrabooks";
  const surfaceErrors = options?.surfaceErrors === true;
  const params = new URLSearchParams({
    document_type: "voucher",
    include_reviewed: includeReviewed ? "true" : "false",
    limit: "100",
  });
  const result = await apiRequest(appKey, `/api/v1/business/approval-queue?${params.toString()}`, { method: "GET" });

  if (result.ok) {
    const items = Array.isArray(result.payload?.items) ? result.payload.items : [];
    lastVoucherApprovalQueue = items;
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastVoucherApprovalQueue = [];
    if (surfaceErrors) {
      setLoginStatus("danger", "Unable to load voucher review queue", statusDetailText(result.payload?.detail) || `Approval queue request failed with HTTP ${result.status}.`);
    }
  }
  renderJson(apiOutput, { approval_queue: { ok: result.ok, status: result.status, count: lastVoucherApprovalQueue.length, detail: result.payload?.detail || null } });
}

async function reviewBusinessVoucher(voucherId, approve, notes, rejectionReason = "") {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/vouchers/${encodeURIComponent(voucherId)}/review`, {
    method: "POST",
    body: JSON.stringify({
      approve,
      notes,
      rejection_reason: rejectionReason || null,
      accounting_entity_id: "primary",
    }),
  });

  if (result.ok) {
    setLoginStatus("ok", approve ? "Voucher approved" : "Voucher rejected", approve ? "Voucher review recorded." : "Voucher rejection recorded.");
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
  } else {
    setLoginStatus("danger", approve ? "Voucher approval failed" : "Voucher rejection failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { review_voucher: result });
}

async function reverseBusinessVoucher(voucherId) {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/vouchers/${encodeURIComponent(voucherId)}/reverse`, {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-reversal-${voucherId}`,
    },
    body: JSON.stringify({
      reason: "Reversal",
    }),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher reversed", "Reversal entry created.");
    await loadBusinessVouchers();
  } else {
    setLoginStatus("danger", "Reverse voucher failed", result.payload?.detail || "Try again.");
  }
  renderJson(apiOutput, { reverse_voucher: result });
}

/**
 * Render form fields for specific voucher type
 */
function renderVoucherTypeForm(voucherType) {
  const accountSelector = (fieldId) => renderAccountSelectorComponent(fieldId);
  const costCentreOptions = dimensionOptions("cost_centre");
  const projectOptions = dimensionOptions("project");
  const dimensionFields = (costCentreOptions || projectOptions) ? `
        <div class="report-date-controls voucher-dimension-fields">
          ${costCentreOptions ? `<label>Cost centre <select id="business-voucher-cost-centre">${costCentreOptions}</select></label>` : ""}
          ${projectOptions ? `<label>Project <select id="business-voucher-project">${projectOptions}</select></label>` : ""}
        </div>` : "";

  if (voucherType === "payment") {
    return `
      <div class="voucher-type-form">
        <div class="voucher-posting-map" aria-label="Payment voucher posting">
          <div>
            <span>Debit</span>
            <strong>Vendor / party ledger</strong>
          </div>
          <div>
            <span>Credit</span>
            <strong>Bank or cash account</strong>
          </div>
        </div>
        <div class="field">
          <label for="business-voucher-party">Party (Vendor/Customer)</label>
          <select id="business-voucher-party" required>
            <option value="">-- Select Party --</option>
            ${Array.isArray(lastBusinessParties) ? lastBusinessParties.map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="voucher-entry-lines">
          <div class="voucher-entry-line debit-line">
            <div>
              <span>Debit</span>
              <strong>Party payable / expense ledger</strong>
            </div>
            ${accountSelector("business-voucher-debit-account")}
          </div>
          <div class="voucher-entry-line credit-line">
            <div>
              <span>Credit</span>
              <strong>Bank / cash ledger</strong>
            </div>
            ${accountSelector("business-voucher-credit-account")}
          </div>
        </div>
        <div class="voucher-balance-panel">
          <strong>Double-entry check</strong>
          <span id="business-voucher-balance" class="voucher-balance-status imbalanced">
            <span>Debit: Rs. 0.00</span>
            <span>Credit: Rs. 0.00</span>
            <strong>Debit must equal Credit</strong>
          </span>
        </div>
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Payment description"></textarea>
        </div>
        <div class="field">
          <label for="business-voucher-reference">Reference (Check #, UTR, etc.)</label>
          <input id="business-voucher-reference" type="text" maxlength="80" placeholder="Optional: check number or reference">
        </div>
      </div>
    `;
  }

  if (voucherType === "receipt") {
    return `
      <div class="voucher-type-form">
        <div class="voucher-posting-map" aria-label="Receipt voucher posting">
          <div>
            <span>Debit</span>
            <strong>Bank or cash account</strong>
          </div>
          <div>
            <span>Credit</span>
            <strong>Customer / party ledger</strong>
          </div>
        </div>
        <div class="field">
          <label for="business-voucher-party">Party (Customer/Vendor)</label>
          <select id="business-voucher-party" required>
            <option value="">-- Select Party --</option>
            ${Array.isArray(lastBusinessParties) ? lastBusinessParties.map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="voucher-entry-lines">
          <div class="voucher-entry-line debit-line">
            <div>
              <span>Debit</span>
              <strong>Bank / cash ledger</strong>
            </div>
            ${accountSelector("business-voucher-debit-account")}
          </div>
          <div class="voucher-entry-line credit-line">
            <div>
              <span>Credit</span>
              <strong>Customer receivable / party ledger</strong>
            </div>
            ${accountSelector("business-voucher-credit-account")}
          </div>
        </div>
        <div class="voucher-balance-panel">
          <strong>Double-entry check</strong>
          <span id="business-voucher-balance" class="voucher-balance-status imbalanced">
            <span>Debit: Rs. 0.00</span>
            <span>Credit: Rs. 0.00</span>
            <strong>Debit must equal Credit</strong>
          </span>
        </div>
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Receipt description"></textarea>
        </div>
        <div class="field">
          <label for="business-voucher-reference">Reference (Invoice #, etc.)</label>
          <input id="business-voucher-reference" type="text" maxlength="80" placeholder="Optional: invoice number or reference">
        </div>
      </div>
    `;
  }

  if (voucherType === "contra") {
    return `
      <div class="voucher-type-form">
        <div class="field">
          <label>From Account</label>
          ${accountSelector("business-voucher-from-account")}
        </div>
        <div class="field">
          <label>To Account</label>
          ${accountSelector("business-voucher-to-account")}
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Transfer description (e.g., sweep to savings)"></textarea>
        </div>
      </div>
    `;
  }

  if (voucherType === "journal") {
    return `
      <div class="voucher-type-form">
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Journal entry description" required></textarea>
        </div>
        <div class="voucher-lines-panel">
          <h4>Debit/Credit Lines</h4>
          <p class="muted" id="business-voucher-accounts-status">Select accounts and enter amounts.</p>
          <div id="business-voucher-lines"></div>
          <button class="secondary" type="button" id="business-voucher-add-line" aria-keyshortcuts="Alt+L">+ Add Line</button>
        </div>
        ${dimensionFields}
        <div class="voucher-balance-panel">
          <strong>Balance Check:</strong>
          <span id="business-voucher-balance" style="font-weight: bold; margin-left: 8px;">Debit: ₹0 | Credit: ₹0</span>
        </div>
      </div>
    `;
  }

  return `<p class="muted">Select a voucher type to proceed.</p>`;
}

/**
 * Update form when voucher type changes
 */
function updateVoucherTypeForm(voucherType) {
  const container = document.getElementById("business-voucher-form-container");
  if (!container) return;

  container.innerHTML = renderVoucherTypeForm(voucherType);

  // For journal entries, add initial lines
  if (voucherType === "journal") {
    addVoucherLine();
    addVoucherLine();
  }

  document.getElementById("business-voucher-add-line")?.addEventListener("click", (event) => {
    event.preventDefault();
    addVoucherLine();
  });

  // Re-attach event listeners for new elements
  updateVoucherBalance();
}

function focusFirstVoucherField() {
  const firstField = document.getElementById("business-voucher-type-select");
  if (firstField) {
    setTimeout(() => firstField.focus(), 0);
  }
}

function submitVoucherDialogFromKeyboard() {
  const submitButton = document.getElementById("business-voucher-submit");
  if (!submitButton || submitButton.disabled) {
    return;
  }
  businessVoucherCreateForm?.requestSubmit();
}

function handleVoucherDialogKeyboard(event) {
  if (!businessVoucherCreateDialog?.open) {
    return;
  }
  if (event.key === "Enter" && event.ctrlKey) {
    event.preventDefault();
    submitVoucherDialogFromKeyboard();
    return;
  }
  if (event.key.toLowerCase() === "l" && event.altKey) {
    const voucherType = document.getElementById("business-voucher-type-select")?.value || "";
    if (voucherType === "journal") {
      event.preventDefault();
      addVoucherLine();
    }
  }
}

async function openBusinessCreateVoucherDialog() {
  const dialog = document.getElementById("business-voucher-create-dialog");
  if (!dialog) return;

  if (!Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0) {
    await loadBusinessAccounts();
  }
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) {
    await loadBusinessParties();
  }
  if (!lastDimensions) {
    await loadDimensions();
  }

  // Reset form
  document.getElementById("business-voucher-type-select").value = "";
  document.getElementById("business-voucher-form-container").innerHTML = "";
  document.getElementById("business-voucher-date").valueAsDate = new Date();

  if (!Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0) {
    setLoginStatus("warn", "Accounts unavailable", "Load the MitraBooks chart of accounts before posting a voucher.");
  }

  dialog.showModal();
  focusFirstVoucherField();
}


async function runChecks() {
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const tokenAtStart = getAccessToken();
  const health = await loadHealth(activeAppKey);
  healthPill.textContent = statusLabel(health);
  healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;

  const modules = await loadModules(activeAppKey);
  if (modules.ok) {
    lastModuleContext = modules.payload;
    updateTrustedContextUi(lastModuleContext);
    updateSessionUi();
  }
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (!modules.ok && modules.status === 401) {
    // Ignore stale unauthenticated 401s that finish after a concurrent login.
    if (getAccessToken() && getAccessToken() !== tokenAtStart) {
      return;
    }
    lastModuleContext = null;
    clearAllTokens();
    renderModules();
    if (!isPasswordRecoveryPanelOpen()) {
      setLoginStatus("warn", "Sign in required", "Enter your email and password to load tenant data.");
    }
    updateSessionUi();
    return;
  }

  if (!modules.ok && currentExperience === "mitrabooks") {
    lastModuleContext = null;
    // Treat network/timeout failures the same as 401 when a cached token cannot
    // establish tenant context, so hosted smoke does not keep a dead session.
    if (tokenAtStart && getAccessToken() === tokenAtStart) {
      clearAllTokens();
      renderModules();
      if (!isPasswordRecoveryPanelOpen()) {
        setLoginStatus("warn", "Sign in required", "Enter your email and password to load tenant data.");
      }
      updateSessionUi();
      return;
    }
    renderModules();
    if (!isPasswordRecoveryPanelOpen()) {
      setLoginStatus("warn", "Tenant session required", "Sign in to load your MitraBooks dashboard.");
    }
    updateSessionUi();
    return;
  }

  if (modules.ok && currentExperience === "mitrabooks" && isPlatformOwnerContext(modules.payload)) {
    currentExperience = "platform";
    document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
    document.getElementById("mode-platform")?.classList.add("active");
    renderModules();
    setLoginStatus("ok", "Platform owner signed in", "Showing the platform-owner workspace. Business tenant data remains tenant-scoped.");
    updateSessionUi();
    await loadPlatformOwnerDashboard();
    return;
  }

  if (modules.ok && currentExperience === "mitrabooks") {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules();
  }

  if (currentExperience === "platform") {
    await loadPlatformOwnerDashboard();
  } else if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else if (currentExperience === "gruha") {
    await loadGruhaDashboard();
  } else if (currentExperience === "mitrabooks") {
    await loadBusinessAccounts();
    await loadBusinessPartiesForHealth();
    const accountingDrilldown = await loadAccountingDrilldownResult();
    renderJson(apiOutput, { health, modules, accounting_drilldown: accountingDrilldown });
    refreshBooksHealthWidget();
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function loadPlatformOwnerDashboard() {
  const result = await apiRequest(APP_KEY, "/api/v1/platform-owner/dashboard", { method: "GET" });
  renderJson(apiOutput, { platform_owner_dashboard: result });
  if (result.ok) {
    lastPlatformOwnerDashboard = result.payload;
    dashboardPreview.innerHTML = renderPlatformDashboard(result.payload);
    syncPlatformNavActiveState();
    return;
  }

  dashboardPreview.insertAdjacentHTML(
    "afterbegin",
    `<div class="module-state warn"><strong>Platform dashboard unavailable</strong><span>Provide a super-admin access token and run checks to load live platform-owner data.</span></div>`
  );
}

function buildQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      query.set(key, String(value).trim());
    }
  });
  return query.toString();
}

function mandirListPath(kind) {
  const state = mandirListState[kind] || {};
  const path = kind === "sevas" ? "/api/v1/sevas/bookings" : "/api/v1/donations";
  const query = buildQueryString({
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    from_date: state.from_date,
    to_date: state.to_date,
    payment_mode: kind === "donations" ? state.payment_mode : "",
    status: kind === "sevas" ? state.status : "",
  });
  return `${path}?${query}`;
}

function mandirPublicPaymentsPath() {
  const state = mandirListState.payments;
  const query = buildQueryString({
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    status: state.status || "pending",
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments?${query}`;
}

function mandirPublicPaymentExceptionsPath() {
  const state = mandirListState.exceptions;
  const query = buildQueryString({
    older_than_hours: 24,
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    reason: state.reason,
    status: state.status,
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments/exceptions?${query}`;
}

function accountingDrilldownPath() {
  const state = accountingDrilldownState;
  const query = buildQueryString({
    from_date: state.from_date,
    to_date: state.to_date,
    level: state.level,
    month: state.month,
    week_start: state.week_start,
    day: state.day,
  });
  return `/api/v1/accounting/reports/drilldown?${query}`;
}

async function loadAccountingDrilldownResult() {
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const result = await apiRequest(activeAppKey, accountingDrilldownPath(), { method: "GET" });
  lastAccountingDrilldown = result.ok ? result.payload : result;
  return result;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNTING DRILLDOWN (shared MandirMitra + MitraBooks)
// API   : GET /api/v1/accounting/drilldown/...
// NOTE  : loadAccountingVoucherDetail, renderAccountingDrilldownPanel
// ══════════════════════════════════════════════════════════════════════

async function loadAccountingVoucherDetail(journalId) {
  if (!journalId) {
    return null;
  }
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const result = await apiRequest(activeAppKey, `/api/v1/accounting/reports/vouchers/${encodeURIComponent(journalId)}`, { method: "GET" });
  lastAccountingVoucherDetail = result.ok ? result.payload : result;
  return result;
}

async function loadMandirDashboard() {
  const reportRangeQuery = buildQueryString({
    from_date: accountingDrilldownState.from_date,
    to_date: accountingDrilldownState.to_date,
  });
  const asOf = encodeURIComponent(todayIsoDate());
  const [
    stats, pendingPayments, paymentExceptions, donations, sevaBookings, paymentAccounts, accounts, expenses,
    trialBalance, incomeExpenditure, receiptsPayments, balanceSheet, panchang, moduleConfig, complianceConfig,
    donationCategoryReport, donationDetailReport, sevaDetailReport, sevaScheduleReport, devoteesReport,
    compliance80gReport, complianceFcraReport, fundWiseReport, festivalWiseReport, fundSubledgerReport,
    fundsAsOfReport, fundTransfers, fundOpeningBalances, inventorySummary, inventoryStockBalances,
    inventoryMovements, inventoryConsumptions, accountingDrilldown,
  ] = await Promise.all([
    apiRequest("mandirmitra", "/api/v1/dashboard/stats", { method: "GET" }),
    apiRequest("mandirmitra", mandirPublicPaymentsPath(), { method: "GET" }),
    apiRequest("mandirmitra", mandirPublicPaymentExceptionsPath(), { method: "GET" }),
    apiRequest("mandirmitra", mandirListPath("donations"), { method: "GET" }),
    apiRequest("mandirmitra", mandirListPath("sevas"), { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/donations/payment-accounts", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/accounts", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/journal-entries?reference_type=expense&limit=25", { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/journal-entries/reports/trial-balance?as_of=${asOf}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/journal-entries/reports/income-expenditure?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/journal-entries/reports/receipts-payments?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/journal-entries/reports/balance-sheet?as_of=${asOf}`, { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/panchang/today", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/temples/modules/config", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/compliance/donations/config", { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/donations/category-wise?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/donations/detailed?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/sevas/detailed?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/reports/sevas/schedule?days=30", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/devotees?limit=50", { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/compliance/80g?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/compliance/fcra?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/donations/fund-wise?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/donations/festival-wise?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/funds/subledger?${reportRangeQuery}`, { method: "GET" }),
    apiRequest("mandirmitra", `/api/v1/reports/funds/as-of?as_of=${asOf}`, { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/fund-transfers", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/fund-opening-balances", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/inventory/summary", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/inventory/stock-balances", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/inventory/movements", { method: "GET" }),
    apiRequest("mandirmitra", "/api/v1/inventory/consumptions", { method: "GET" }),
    loadAccountingDrilldownResult(),
  ]);
  if (paymentAccounts.ok) {
    lastMandirPaymentAccounts = paymentAccounts.payload || { cash_accounts: [], bank_accounts: [] };
  }
  if (accounts.ok && Array.isArray(accounts.payload)) {
    lastMandirAccounts = accounts.payload;
  }
  if (expenses.ok && Array.isArray(expenses.payload)) {
    mandirReportState.expenses = expenses.payload;
  }
  mandirReportState.trialBalance = trialBalance.ok ? trialBalance.payload : trialBalance;
  mandirReportState.financialReports = {
    income_expenditure: incomeExpenditure.ok ? incomeExpenditure.payload : incomeExpenditure,
    receipts_payments: receiptsPayments.ok ? receiptsPayments.payload : receiptsPayments,
    balance_sheet: balanceSheet.ok ? balanceSheet.payload : balanceSheet,
  };
  lastMandirPanchang = panchang.ok ? panchang.payload : panchang;
  lastMandirModuleConfig = moduleConfig.ok ? moduleConfig.payload : lastMandirModuleConfig;
  lastMandirComplianceConfig = complianceConfig.ok ? complianceConfig.payload : lastMandirComplianceConfig;
  lastMandirOperationalReports = {
    donation_category: donationCategoryReport.ok ? donationCategoryReport.payload : donationCategoryReport,
    donation_detail: donationDetailReport.ok ? donationDetailReport.payload : donationDetailReport,
    seva_detail: sevaDetailReport.ok ? sevaDetailReport.payload : sevaDetailReport,
    seva_schedule: sevaScheduleReport.ok ? sevaScheduleReport.payload : sevaScheduleReport,
    devotees: devoteesReport.ok && Array.isArray(devoteesReport.payload) ? devoteesReport.payload : [],
    compliance_80g: compliance80gReport.ok ? compliance80gReport.payload : compliance80gReport,
    compliance_fcra: complianceFcraReport.ok ? complianceFcraReport.payload : complianceFcraReport,
    fund_wise: fundWiseReport.ok ? fundWiseReport.payload : fundWiseReport,
    festival_wise: festivalWiseReport.ok ? festivalWiseReport.payload : festivalWiseReport,
    fund_subledger: fundSubledgerReport.ok ? fundSubledgerReport.payload : fundSubledgerReport,
    funds_as_of: fundsAsOfReport.ok ? fundsAsOfReport.payload : fundsAsOfReport,
    fund_transfers: fundTransfers.ok && Array.isArray(fundTransfers.payload) ? fundTransfers.payload : [],
    fund_opening_balances: fundOpeningBalances.ok && Array.isArray(fundOpeningBalances.payload) ? fundOpeningBalances.payload : [],
    inventory_summary: inventorySummary.ok ? inventorySummary.payload : inventorySummary,
    inventory_stock_balances: inventoryStockBalances.ok && Array.isArray(inventoryStockBalances.payload) ? inventoryStockBalances.payload : [],
    inventory_movements: inventoryMovements.ok && Array.isArray(inventoryMovements.payload) ? inventoryMovements.payload : [],
    inventory_consumptions: inventoryConsumptions.ok && Array.isArray(inventoryConsumptions.payload) ? inventoryConsumptions.payload : [],
    inventory_enabled: Boolean((moduleConfig.ok ? moduleConfig.payload : lastMandirModuleConfig)?.module_inventory_enabled),
  };
  renderJson(apiOutput, {
    mandir_dashboard_stats: stats,
    mandir_pending_public_payments: pendingPayments,
    mandir_payment_exceptions: paymentExceptions,
    mandir_recent_donations: donations,
    mandir_recent_seva_bookings: sevaBookings,
    mandir_payment_accounts: paymentAccounts,
    mandir_accounts: accounts,
    mandir_recent_expenses: expenses,
    mandir_trial_balance: trialBalance,
    mandir_income_expenditure: incomeExpenditure,
    mandir_receipts_payments: receiptsPayments,
    mandir_balance_sheet: balanceSheet,
    mandir_panchang: panchang,
    mandir_module_config: moduleConfig,
    mandir_compliance_config: complianceConfig,
    mandir_donation_category_report: donationCategoryReport,
    mandir_donation_detail_report: donationDetailReport,
    mandir_seva_detail_report: sevaDetailReport,
    mandir_seva_schedule_report: sevaScheduleReport,
    mandir_devotees_report: devoteesReport,
    mandir_80g_readiness_report: compliance80gReport,
    mandir_fcra_readiness_report: complianceFcraReport,
    mandir_fund_subledger_report: fundSubledgerReport,
    mandir_funds_as_of_report: fundsAsOfReport,
    mandir_inventory_summary: inventorySummary,
    mandir_inventory_stock_balances: inventoryStockBalances,
    accounting_drilldown: accountingDrilldown,
  });
  const hasLiveData = stats.ok || pendingPayments.ok || paymentExceptions.ok || donations.ok || sevaBookings.ok;
  dashboardPreview.innerHTML = renderMandirDashboard({
    stats: stats.ok ? stats.payload : {},
    pending_payments: pendingPayments.ok && Array.isArray(pendingPayments.payload) ? pendingPayments.payload : [],
    payment_exceptions: paymentExceptions.ok && Array.isArray(paymentExceptions.payload?.items) ? paymentExceptions.payload.items : [],
    payment_exception_summary: paymentExceptions.ok ? paymentExceptions.payload?.summary : {},
    recent_receipts: mandirReceiptRowsFromLists(
      donations.ok && Array.isArray(donations.payload) ? donations.payload : [],
      sevaBookings.ok && Array.isArray(sevaBookings.payload) ? sevaBookings.payload : []
    ),
    recent_donations: donations.ok && Array.isArray(donations.payload) ? donations.payload : [],
    recent_seva_bookings: sevaBookings.ok && Array.isArray(sevaBookings.payload) ? sevaBookings.payload : [],
    recent_expenses: expenses.ok && Array.isArray(expenses.payload) ? expenses.payload : mandirReportState.expenses,
    trial_balance: mandirReportState.trialBalance,
    financial_reports: mandirReportState.financialReports,
    panchang: lastMandirPanchang,
    operational_reports: lastMandirOperationalReports,
    module_config: lastMandirModuleConfig,
    compliance_config: lastMandirComplianceConfig,
    payment_accounts: paymentAccounts.ok ? paymentAccounts.payload : lastMandirPaymentAccounts,
    accounts: accounts.ok && Array.isArray(accounts.payload) ? accounts.payload : lastMandirAccounts,
    receipt: lastMandirReceipt,
    form_result: lastMandirFormResult,
    live_data_available: hasLiveData,
  });
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — account options / create forms / posting dialogs
// API   : POST /api/v1/mandir/... (receipts, seva bookings, expenses, contra)
// ══════════════════════════════════════════════════════════════════════

function renderBankAccountOptions(accounts = []) {
  const options = ['<option value="">Use backend default bank account</option>'];
  accounts.forEach((account) => {
    const accountId = account.account_id || account.id || "";
    if (!accountId) {
      return;
    }
    const accountCode = account.account_code ? `${account.account_code} - ` : "";
    const accountName = account.account_name || account.name || "Bank account";
    options.push(`<option value="${escapeHtml(accountId)}">${escapeHtml(`${accountCode}${accountName}`)}</option>`);
  });
  return options.join("");
}

function mandirAccountOptionValue(account = {}) {
  return account.account_id || account.id || account.account_code || "";
}

function mandirAccountOptionLabel(account = {}) {
  const code = account.account_code ? `${account.account_code} - ` : "";
  return `${code}${account.account_name || account.name || "Account"}`;
}

function renderMandirAccountOptions(accounts = [], placeholder = "Select account") {
  const options = [`<option value="">${escapeHtml(placeholder)}</option>`];
  accounts.forEach((account) => {
    const value = mandirAccountOptionValue(account);
    if (!value) {
      return;
    }
    options.push(`<option value="${escapeHtml(value)}">${escapeHtml(mandirAccountOptionLabel(account))}</option>`);
  });
  return options.join("");
}

function mandirPaymentAccountOptions(paymentAccounts = lastMandirPaymentAccounts) {
  return [
    ...(Array.isArray(paymentAccounts.cash_accounts) ? paymentAccounts.cash_accounts : []),
    ...(Array.isArray(paymentAccounts.bank_accounts) ? paymentAccounts.bank_accounts : []),
  ];
}

function mandirExpenseAccountOptions(accounts = lastMandirAccounts) {
  return accounts.filter((account) => {
    const type = String(account.account_type || "").toLowerCase();
    const name = String(account.account_name || account.name || "").toLowerCase();
    return type === "expense" || name.includes("expense");
  });
}

function renderMandirCreateForms(payload = {}) {
  const paymentOptions = renderMandirAccountOptions(
    mandirPaymentAccountOptions(payload.payment_accounts),
    "Use default cash/bank"
  );
  const expenseOptions = renderMandirAccountOptions(
    mandirExpenseAccountOptions(payload.accounts),
    "Select expense account"
  );
  const today = todayIsoDate();
  const result = payload.form_result || lastMandirFormResult;
  const inventoryEnabled = Boolean(payload.module_config?.module_inventory_enabled);
  const complianceConfig = payload.compliance_config || {};
  const inKindAccountingLabel = inventoryEnabled
    ? "In-kind consumables debit inventory"
    : "In-kind consumables debit expense";
  return `
    <div class="quick-entry-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Daily Entry</h4>
          <p>Record donations, seva bookings, and temple expenses for the active temple tenant.</p>
        </div>
        <span class="pill technical-context">${escapeHtml(inKindAccountingLabel)}</span>
      </div>
      ${result ? `
        <div class="module-state ${result.ok ? "ok" : "warn"}">
          <strong>${escapeHtml(result.title || (result.ok ? "Entry saved" : "Entry failed"))}</strong>
          <span>${escapeHtml(result.detail || "")}</span>
        </div>
      ` : ""}
      <div class="entry-form-grid">
        <form class="entry-form" data-mandir-create-form="donation">
          <h5>Donation</h5>
          <label class="field">
            <span>Devotee</span>
            <input name="devotee_name" required maxlength="120" placeholder="Devotee name">
          </label>
          <label class="field">
            <span>Phone</span>
            <input name="devotee_phone" inputmode="numeric" maxlength="15" placeholder="Optional">
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="501">
          </label>
          <label class="field">
            <span>Category</span>
            <select name="category">
              <option value="General Donation">General Donation</option>
              <option value="Sponsorship">Sponsorship</option>
              <option value="Annadanam">Annadanam</option>
              <option value="Flower Decoration">Flower Decoration</option>
              <option value="Lighting Sponsorship">Lighting Sponsorship</option>
              <option value="Vastra Seva">Vastra Seva</option>
              <option value="Nitya Puja">Nitya Puja</option>
              <option value="Construction Fund">Construction Fund</option>
              <option value="Corpus Fund">Corpus Fund</option>
            </select>
          </label>
          <label class="field">
            <span>Donation type</span>
            <select name="donation_type">
              <option value="cash">Cash / bank</option>
              <option value="in_kind">In-kind valued</option>
            </select>
          </label>
          <label class="field">
            <span>Event / festival</span>
            <input name="event_name" maxlength="160" placeholder="Annadanam, Deepotsava">
          </label>
          <label class="field">
            <span>Item name</span>
            <input name="in_kind_item_name" maxlength="160" placeholder="Rice bags, gold ornament">
          </label>
          <label class="field">
            <span>Item type</span>
            <select name="in_kind_item_type">
              <option value="">Not applicable</option>
              <option value="rice">Rice / food grains</option>
              <option value="dal">Dal</option>
              <option value="oil">Oil / ghee</option>
              <option value="flower decoration">Flower decoration</option>
              <option value="lighting">Lighting</option>
              <option value="gold ornament">Gold ornament</option>
              <option value="silver article">Silver article</option>
              <option value="idol">Idol / vigraha</option>
              <option value="pooja material">Pooja material</option>
            </select>
          </label>
          <label class="field">
            <span>Quantity</span>
            <input name="in_kind_quantity" maxlength="80" placeholder="50 kg, 2 bags, 1 item">
          </label>
          <label class="field">
            <span>Valuation basis</span>
            <input name="in_kind_valuation_basis" maxlength="180" placeholder="Market value, invoice, trustee valuation">
          </label>
          <label class="field">
            <span>Payment mode</span>
            <select name="payment_mode">
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
              <option value="UPI">UPI</option>
            </select>
          </label>
          <label class="field">
            <span>Cash/bank account</span>
            <select name="payment_account_id">${paymentOptions}</select>
          </label>
          <label class="field">
            <span><input name="request_80g" type="checkbox" ${complianceConfig.enable_80g ? "" : "disabled"}> Request 80G eligibility review</span>
            <small>${complianceConfig.enable_80g ? "Requires donor PAN and tenant approval validity." : "80G is off for this tenant."}</small>
          </label>
          <label class="field">
            <span>Donor PAN</span>
            <input name="donor_pan" maxlength="10" pattern="[A-Za-z]{5}[0-9]{4}[A-Za-z]" placeholder="Required when 80G is requested" ${complianceConfig.enable_80g ? "" : "disabled"}>
          </label>
          <label class="field">
            <span><input name="is_foreign_contribution" type="checkbox" ${complianceConfig.enable_fcra ? "" : "disabled"}> Foreign contribution</span>
            <small>${complianceConfig.enable_fcra ? `Must use designated account ${escapeHtml(complianceConfig.fcra_designated_account_id || "configured by admin")}.` : "FCRA is off for this tenant."}</small>
          </label>
          <label class="field">
            <span>Donor country</span>
            <input name="donor_country" maxlength="100" placeholder="Required for foreign contribution" ${complianceConfig.enable_fcra ? "" : "disabled"}>
          </label>
          <label class="field">
            <span><input name="foreign_source_declaration" type="checkbox" ${complianceConfig.enable_fcra ? "" : "disabled"}> Foreign-source declaration confirmed</span>
          </label>
          <button type="submit">Create Donation</button>
        </form>

        <form class="entry-form" data-mandir-create-form="seva">
          <h5>Seva Booking</h5>
          <label class="field">
            <span>Devotee</span>
            <input name="devotee_name" required maxlength="120" placeholder="Devotee name">
          </label>
          <label class="field">
            <span>Phone</span>
            <input name="devotee_phone" inputmode="numeric" maxlength="15" placeholder="Optional">
          </label>
          <label class="field">
            <span>Seva</span>
            <input name="seva_name" required maxlength="160" placeholder="Archana">
          </label>
          <label class="field">
            <span>Booking date</span>
            <input name="booking_date" type="date" value="${escapeHtml(today)}" required>
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="301">
          </label>
          <label class="field">
            <span>Payment mode</span>
            <select name="payment_mode">
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
              <option value="UPI">UPI</option>
            </select>
          </label>
          <label class="field">
            <span>Cash/bank account</span>
            <select name="payment_account_id">${paymentOptions}</select>
          </label>
          <button type="submit">Create Seva Booking</button>
        </form>

        <form class="entry-form" data-mandir-create-form="expense">
          <h5>Quick Expense</h5>
          <label class="field">
            <span>Narration</span>
            <input name="narration" required maxlength="160" placeholder="Flowers and pooja material">
          </label>
          <label class="field">
            <span>Entry date</span>
            <input name="entry_date" type="date" value="${escapeHtml(today)}" required>
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="250">
          </label>
          <label class="field">
            <span>Expense account</span>
            <select name="expense_account_id" required>${expenseOptions}</select>
          </label>
          <label class="field">
            <span>Paid from</span>
            <select name="payment_account_id" required>${paymentOptions}</select>
          </label>
          <button type="submit">Create Expense</button>
        </form>
      </div>
    </div>
  `;
}

async function openMandirVerificationDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  const paymentType = button.getAttribute("data-payment-type") || "payment";
  const devoteeName = button.getAttribute("data-devotee-name") || "Devotee";
  const amount = formatCurrency(button.getAttribute("data-payment-amount") || 0);

  mandirVerificationPaymentId.value = paymentId;
  mandirVerificationUtr.value = "";
  mandirVerificationDate.value = todayIsoDate();
  mandirVerificationLabel.textContent = `${paymentLabel} | ${paymentType} | ${devoteeName} | ${amount}`;
  mandirVerificationBankAccount.innerHTML = '<option value="">Loading bank accounts...</option>';
  mandirVerificationDialog.showModal();

  const accounts = await apiRequest("mandirmitra", "/api/v1/donations/payment-accounts", { method: "GET" });
  if (accounts.ok) {
    const bankAccounts = Array.isArray(accounts.payload?.bank_accounts) ? accounts.payload.bank_accounts : [];
    mandirVerificationBankAccount.innerHTML = renderBankAccountOptions(bankAccounts);
  } else {
    mandirVerificationBankAccount.innerHTML = '<option value="">Use backend default bank account</option>';
    renderJson(apiOutput, { mandir_payment_accounts: accounts });
  }
}

function mandirReceiptFromVerifyPayload(payload) {
  const receiptPdfUrl = String(payload?.receipt_pdf_url || "").trim();
  if (!receiptPdfUrl) {
    return null;
  }
  const receiptNumber = String(payload?.receipt_number || payload?.payment_id || "receipt").trim();
  const safeReceiptNumber = receiptNumber.replace(/[^a-z0-9_-]+/gi, "_") || "receipt";
  return {
    receipt_pdf_url: receiptPdfUrl,
    receipt_number: receiptNumber,
    source_id: payload?.source_id,
    source_type: payload?.source_type,
    filename: `${safeReceiptNumber}.pdf`,
  };
}

async function submitMandirPublicPaymentVerification() {
  const paymentId = mandirVerificationPaymentId.value;
  if (!paymentId) {
    return;
  }
  const utrReference = mandirVerificationUtr.value.trim().replace(/\s+/g, " ");
  if (!/^[A-Za-z0-9][A-Za-z0-9 ._:/-]{3,79}$/.test(utrReference)) {
    mandirVerificationUtr.setCustomValidity("Enter a valid UTR/reference, 4-80 characters.");
    mandirVerificationUtr.reportValidity();
    return;
  }
  mandirVerificationUtr.setCustomValidity("");
  const payload = {
    utr_reference: utrReference,
    payment_date: mandirVerificationDate.value || todayIsoDate(),
  };
  if (mandirVerificationBankAccount.value) {
    payload.bank_account_id = mandirVerificationBankAccount.value;
  }

  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/verify`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { verify_mandir_public_payment: result });
  if (result.ok) {
    lastMandirReceipt = mandirReceiptFromVerifyPayload(result.payload);
  }
  mandirVerificationDialog.close();
  await loadMandirDashboard();
}

function openMandirRejectionDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  mandirRejectionPaymentId.value = paymentId;
  mandirRejectionLabel.textContent = `Reject ${paymentLabel}`;
  mandirRejectionReason.value = "";
  mandirRejectionDialog.showModal();
}

async function submitMandirPublicPaymentRejection() {
  const paymentId = mandirRejectionPaymentId.value;
  const reason = mandirRejectionReason.value.trim().replace(/\s+/g, " ");
  if (reason.length < 3) {
    mandirRejectionReason.setCustomValidity("Enter a rejection reason.");
    mandirRejectionReason.reportValidity();
    return;
  }
  mandirRejectionReason.setCustomValidity("");
  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/reject`, {
    method: "PATCH",
    body: JSON.stringify({ reason }),
  });
  renderJson(apiOutput, { reject_mandir_public_payment: result });
  mandirRejectionDialog.close();
  await loadMandirDashboard();
}

function openMandirCorrectionDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  mandirCorrectionPaymentId.value = paymentId;
  mandirCorrectionLabel.textContent = `Correct ${paymentLabel}`;
  mandirCorrectionAmount.value = button.getAttribute("data-payment-amount") || "";
  mandirCorrectionPhone.value = button.getAttribute("data-devotee-phone") || "";
  const type = button.getAttribute("data-payment-type") || "donation";
  mandirCorrectionType.value = ["donation", "seva"].includes(type) ? type : "donation";
  mandirCorrectionPurpose.value = button.getAttribute("data-payment-purpose") || "";
  mandirCorrectionDialog.showModal();
}

async function submitMandirPublicPaymentCorrection() {
  const paymentId = mandirCorrectionPaymentId.value;
  const amount = Number(mandirCorrectionAmount.value || 0);
  const phone = mandirCorrectionPhone.value.replace(/\D/g, "").slice(-10);
  const purpose = mandirCorrectionPurpose.value.trim().replace(/\s+/g, " ");
  if (!paymentId || amount <= 0 || phone.length !== 10 || purpose.length < 1) {
    mandirCorrectionForm.reportValidity();
    return;
  }

  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/correction`, {
    method: "PATCH",
    body: JSON.stringify({
      amount,
      devotee_phone: phone,
      payment_type: mandirCorrectionType.value,
      seva_name: purpose,
    }),
  });
  renderJson(apiOutput, { correct_mandir_public_payment: result });
  mandirCorrectionDialog.close();
  await loadMandirDashboard();
}

async function downloadMandirReceipt(button) {
  const receiptUrl = button.getAttribute("data-receipt-url") || "";
  if (!receiptUrl) {
    return;
  }
  const filename = button.getAttribute("data-receipt-filename") || "mandir-receipt.pdf";
  const result = await downloadApiFile("mandirmitra", receiptUrl, filename, { timeoutMs: 15000 });
  renderJson(apiOutput, { download_mandir_receipt: result });
}

function closeReceiptPreview() {
  receiptPreviewDialog.close();
  receiptPreviewFrame.removeAttribute("src");
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
    activeReceiptPreviewObjectUrl = "";
  }
}

async function previewMandirReceipt(button) {
  const receiptUrl = button.getAttribute("data-receipt-url") || "";
  if (!receiptUrl) {
    return;
  }
  const receiptLabel = button.getAttribute("data-receipt-label") || "Receipt PDF";
  const result = await fetchApiFileObjectUrl("mandirmitra", receiptUrl, { timeoutMs: 15000 });
  renderJson(apiOutput, { preview_mandir_receipt: result.ok ? { ...result, payload: { content_type: result.payload.content_type } } : result });
  if (!result.ok) {
    return;
  }
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
  }
  activeReceiptPreviewObjectUrl = result.payload.object_url;
  receiptPreviewLabel.textContent = receiptLabel;
  receiptPreviewFrame.src = activeReceiptPreviewObjectUrl;
  receiptPreviewDialog.showModal();
}

function openMandirCancelReceiptDialog(button) {
  const cancelUrl = button.getAttribute("data-cancel-url") || "";
  if (!cancelUrl) {
    return;
  }
  const receiptLabel = button.getAttribute("data-receipt-label") || "receipt";
  mandirCancelReceiptUrl.value = cancelUrl;
  mandirCancelReceiptLabel.textContent = `Reverse ${receiptLabel} without editing the original receipt.`;
  mandirCancelReceiptReason.value = "";
  mandirCancelRefundMode.value = "";
  mandirCancelRefundReference.value = "";
  mandirCancelReceiptSubmit.disabled = false;
  mandirCancelReceiptSubmit.textContent = "Reverse Receipt";
  mandirCancelReceiptDialog.showModal();
  mandirCancelReceiptReason.focus();
}

async function submitMandirCancelReceipt() {
  const cancelUrl = mandirCancelReceiptUrl.value;
  const receiptLabel = mandirCancelReceiptLabel.textContent || "Receipt";
  const reason = String(mandirCancelReceiptReason.value || "").trim().replace(/\s+/g, " ");
  if (reason.length < 3) {
    return;
  }
  const refundMode = String(mandirCancelRefundMode.value || "").trim().replace(/\s+/g, " ");
  const refundReference = String(mandirCancelRefundReference.value || "").trim().replace(/\s+/g, " ");
  mandirCancelReceiptSubmit.disabled = true;
  mandirCancelReceiptSubmit.textContent = "Reversing...";
  mandirCancelReceiptDialog.close();
  setMandirFormResult(null, "Cancelling receipt", receiptLabel);
  await loadMandirDashboard();
  const result = await apiRequest("mandirmitra", cancelUrl, {
    method: "POST",
    timeoutMs: 20000,
    body: JSON.stringify({
      reason,
      refund_mode: refundMode || null,
      refund_reference: refundReference || null,
    }),
  });
  renderJson(apiOutput, { cancel_mandir_receipt: result });
  if (result.ok) {
    setMandirFormResult(true, "Receipt cancelled", result.payload?.receipt_number || receiptLabel);
    await loadMandirDashboard();
  } else {
    setMandirFormResult(false, "Receipt cancellation failed", result.payload?.detail || "Unable to cancel receipt");
    await loadMandirDashboard();
  }
  dashboardPreview.querySelector("#mandir-operation-result")?.scrollIntoView({ behavior: "smooth", block: "center" });
  mandirCancelReceiptSubmit.disabled = false;
  mandirCancelReceiptSubmit.textContent = "Reverse Receipt";
}

function compactOptionalPhone(value) {
  return String(value || "").replace(/\D/g, "").slice(-10);
}

function formNumber(formData, key) {
  return Number(formData.get(key) || 0);
}

function formText(formData, key) {
  return String(formData.get(key) || "").trim().replace(/\s+/g, " ");
}

function setMandirFormResult(ok, title, detail) {
  lastMandirFormResult = { ok, title, detail };
}

function mandirReceiptFromCreatePayload(payload, fallbackType = "receipt") {
  const receiptPdfUrl = String(payload?.receipt_pdf_url || "").trim();
  if (!receiptPdfUrl) {
    return null;
  }
  const receiptNumber = String(payload?.receipt_number || payload?.donation_id || payload?.id || fallbackType).trim();
  const safeReceiptNumber = receiptNumber.replace(/[^a-z0-9_-]+/gi, "_") || fallbackType;
  return {
    receipt_pdf_url: receiptPdfUrl,
    receipt_number: receiptNumber,
    source_id: payload?.donation_id || payload?.id,
    source_type: fallbackType,
    filename: `${safeReceiptNumber}.pdf`,
  };
}

async function submitMandirDonationForm(form) {
  const formData = new FormData(form);
  const amount = formNumber(formData, "amount");
  const paymentAccountId = formText(formData, "payment_account_id");
  const payload = {
    devotee_name: formText(formData, "devotee_name"),
    devotee_phone: compactOptionalPhone(formData.get("devotee_phone")),
    amount,
    category: formText(formData, "category") || "General Donation",
    donation_type: formText(formData, "donation_type") || "cash",
    payment_mode: formText(formData, "payment_mode") || "Cash",
  };
  ["event_name", "in_kind_item_name", "in_kind_item_type", "in_kind_quantity", "in_kind_valuation_basis"].forEach((key) => {
    const value = formText(formData, key);
    if (value) {
      payload[key] = value;
    }
  });
  if (paymentAccountId) {
    payload.payment_account_id = paymentAccountId;
  }
  payload.request_80g = formData.has("request_80g");
  payload.is_foreign_contribution = formData.has("is_foreign_contribution");
  payload.foreign_source_declaration = formData.has("foreign_source_declaration");
  ["donor_pan", "donor_country"].forEach((key) => {
    const value = formText(formData, key);
    if (value) {
      payload[key] = value;
    }
  });

  const result = await apiRequest("mandirmitra", "/api/v1/donations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { create_mandir_donation: result });
  if (result.ok) {
    lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, "donation") || lastMandirReceipt;
    setMandirFormResult(true, "Donation created", result.payload?.receipt_number || result.payload?.donation_id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Donation failed", result.payload?.detail || "Unable to create donation");
  }
  await loadMandirDashboard();
}

async function submitMandirComplianceForm(form) {
  const formData = new FormData(form);
  const payload = {
    enable_80g: formData.has("enable_80g"),
    institution_pan: formText(formData, "institution_pan").toUpperCase(),
    approval_number: formText(formData, "approval_number"),
    approval_valid_from: formText(formData, "approval_valid_from"),
    approval_valid_to: formText(formData, "approval_valid_to"),
    certificate_label: formText(formData, "certificate_label") || "Donation certificate",
    cash_eligibility_limit: formText(formData, "cash_eligibility_limit"),
    cash_rule_effective_from: formText(formData, "cash_rule_effective_from"),
    receipt_disclaimer: formText(formData, "receipt_disclaimer"),
    enable_fcra: formData.has("enable_fcra"),
    fcra_registration_type: formText(formData, "fcra_registration_type") || "registration",
    fcra_registration_number: formText(formData, "fcra_registration_number"),
    fcra_valid_from: formText(formData, "fcra_valid_from"),
    fcra_valid_to: formText(formData, "fcra_valid_to"),
    fcra_designated_account_id: formText(formData, "fcra_designated_account_id"),
  };
  const result = await apiRequest("mandirmitra", "/api/v1/compliance/donations/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { save_mandir_compliance_config: result });
  if (result.ok) {
    lastMandirComplianceConfig = result.payload || { enable_80g: false, enable_fcra: false };
    setMandirFormResult(true, "Compliance configuration saved", "80G/FCRA controls remain governed by tenant approval evidence.");
  } else {
    setMandirFormResult(false, "Compliance configuration failed", result.payload?.detail || "Unable to save compliance settings");
  }
  await loadMandirDashboard();
}

async function submitMandirSevaForm(form) {
  const formData = new FormData(form);
  const paymentAccountId = formText(formData, "payment_account_id");
  const payload = {
    devotee_name: formText(formData, "devotee_name"),
    devotee_phone: compactOptionalPhone(formData.get("devotee_phone")),
    seva_name: formText(formData, "seva_name"),
    booking_date: formText(formData, "booking_date") || todayIsoDate(),
    amount_paid: formNumber(formData, "amount"),
    payment_mode: formText(formData, "payment_mode") || "Cash",
  };
  if (paymentAccountId) {
    payload.payment_account_id = paymentAccountId;
  }

  const result = await apiRequest("mandirmitra", "/api/v1/sevas/bookings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { create_mandir_seva_booking: result });
  if (result.ok) {
    lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, "seva") || lastMandirReceipt;
    setMandirFormResult(true, "Seva booking created", result.payload?.receipt_number || result.payload?.id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Seva booking failed", result.payload?.detail || "Unable to create seva booking");
  }
  await loadMandirDashboard();
}

async function submitMandirExpenseForm(form) {
  const formData = new FormData(form);
  const amount = formNumber(formData, "amount");
  const narration = formText(formData, "narration");
  const expenseAccountId = formText(formData, "expense_account_id");
  const paymentAccountId = formText(formData, "payment_account_id");
  const entryPayload = {
    entry_date: formText(formData, "entry_date") || todayIsoDate(),
    narration,
    reference_type: "expense",
    journal_lines: [
      {
        account_id: expenseAccountId,
        debit_amount: amount,
        credit_amount: 0,
        description: narration,
      },
      {
        account_id: paymentAccountId,
        debit_amount: 0,
        credit_amount: amount,
        description: narration,
      },
    ],
  };

  const createResult = await apiRequest("mandirmitra", "/api/v1/journal-entries", {
    method: "POST",
    body: JSON.stringify(entryPayload),
  });
  if (!createResult.ok) {
    renderJson(apiOutput, { create_mandir_expense: createResult });
    setMandirFormResult(false, "Expense failed", createResult.payload?.detail || "Unable to create expense draft");
    await loadMandirDashboard();
    return;
  }

  const entryId = createResult.payload?.id;
  const postResult = await apiRequest("mandirmitra", `/api/v1/journal-entries/${encodeURIComponent(entryId)}/post`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderJson(apiOutput, { create_mandir_expense: createResult, post_mandir_expense: postResult });
  if (postResult.ok) {
    if (postResult.payload) {
      mandirReportState.expenses = [
        postResult.payload,
        ...mandirReportState.expenses.filter((expense) => String(expense.id || "") !== String(postResult.payload.id || "")),
      ].slice(0, 25);
    }
    setMandirFormResult(true, "Expense posted", postResult.payload?.entry_number || entryId || "Journal entry posted");
    form.reset();
  } else {
    setMandirFormResult(false, "Expense post failed", postResult.payload?.detail || "Expense draft was created but not posted");
  }
  await loadMandirDashboard();
}

async function submitMandirCreateForm(form) {
  const formType = form.getAttribute("data-mandir-create-form") || "";
  if (!form.reportValidity()) {
    return;
  }
  if (formType === "donation") {
    await submitMandirDonationForm(form);
  } else if (formType === "seva") {
    await submitMandirSevaForm(form);
  } else if (formType === "expense") {
    await submitMandirExpenseForm(form);
  }
}

function readMandirListFilterValues(kind) {
  const panel = dashboardPreview.querySelector(`[data-mandir-list="${kind}"]`);
  if (!panel) {
    return null;
  }
  const formData = new FormData();
  panel.querySelectorAll("input[name], select[name]").forEach((input) => {
    formData.set(input.name, input.value.trim());
  });
  if (kind === "payments") {
    return {
      q: String(formData.get("q") || ""),
      status: String(formData.get("status") || "pending"),
      payment_type: String(formData.get("payment_type") || ""),
    };
  }
  if (kind === "exceptions") {
    return {
      q: String(formData.get("q") || ""),
      reason: String(formData.get("reason") || ""),
      status: String(formData.get("status") || ""),
      payment_type: String(formData.get("payment_type") || ""),
    };
  }
  return {
    q: String(formData.get("q") || ""),
    from_date: String(formData.get("from_date") || ""),
    to_date: String(formData.get("to_date") || ""),
    payment_mode: kind === "donations" ? String(formData.get("payment_mode") || "") : "",
    status: kind === "sevas" ? String(formData.get("status") || "") : "",
  };
}

async function applyMandirListFilter(kind) {
  if (!mandirListState[kind]) {
    return;
  }
  const values = readMandirListFilterValues(kind);
  if (!values) {
    return;
  }
  mandirListState[kind] = {
    ...mandirListState[kind],
    ...values,
    offset: 0,
  };
  await loadMandirDashboard();
}

async function resetMandirListFilter(kind) {
  if (!mandirListState[kind]) {
    return;
  }
  Object.keys(mandirListState[kind]).forEach((key) => {
    mandirListState[kind][key] = key === "offset" ? 0 : "";
  });
  if (kind === "payments") {
    mandirListState.payments.status = "pending";
  }
  await loadMandirDashboard();
}

async function pageMandirList(kind, direction) {
  if (!mandirListState[kind]) {
    return;
  }
  const currentOffset = Number(mandirListState[kind].offset || 0);
  const delta = direction === "prev" ? -MANDIR_LIST_PAGE_SIZE : MANDIR_LIST_PAGE_SIZE;
  mandirListState[kind].offset = Math.max(0, currentOffset + delta);
  await loadMandirDashboard();
}

async function setMandirWorkspace(view) {
  const allowedViews = new Set([
    "overview",
    "donations",
    "sevas",
    "book-sevas",
    "seva-bookings",
    "seva-management",
    "reschedule-approval",
    "devotees",
    "payments",
    "exceptions",
    "receipts",
    "panchang",
    "reports",
    "accounting",
    "settings",
    "implementation",
    "platform-owners",
  ]);
  if (!allowedViews.has(view)) {
    return;
  }
  activeMandirWorkspace = view;
  syncMandirNavActiveState();
  await loadMandirDashboard();
  document.querySelector(".content")?.scrollTo({ top: 0, behavior: "smooth" });
}

function readAccountingDrilldownFilterValues() {
  const panel = dashboardPreview.querySelector("[data-accounting-drilldown]");
  if (!panel) {
    return null;
  }
  const formData = new FormData();
  panel.querySelectorAll("input[name], select[name]").forEach((input) => {
    formData.set(input.name, input.value.trim());
  });
  return {
    from_date: String(formData.get("from_date") || accountingDrilldownState.from_date),
    to_date: String(formData.get("to_date") || accountingDrilldownState.to_date),
    level: String(formData.get("level") || "month"),
    month: "",
    week_start: "",
    day: "",
  };
}

async function refreshCurrentAccountingDrilldown() {
  const result = await loadAccountingDrilldownResult();
  renderJson(apiOutput, { accounting_drilldown: result });
  if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "accounting") {
    dashboardPreview.innerHTML = renderAccountingDrilldownPanel();
  } else {
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function applyAccountingDrilldownFilters() {
  const values = readAccountingDrilldownFilterValues();
  if (!values) {
    return;
  }
  accountingDrilldownState = values;
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function resetAccountingDrilldown() {
  accountingDrilldownState = {
    level: "month",
    from_date: firstDayForReports.toISOString().slice(0, 10),
    to_date: todayForReports.toISOString().slice(0, 10),
    month: "",
    week_start: "",
    day: "",
  };
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function drillAccountingReport(button) {
  accountingDrilldownState = {
    ...accountingDrilldownState,
    level: button.getAttribute("data-next-level") || "month",
    month: button.getAttribute("data-month") || accountingDrilldownState.month || "",
    week_start: button.getAttribute("data-week-start") || "",
    day: button.getAttribute("data-day") || "",
  };
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function openAccountingVoucherDetail(button) {
  const journalId = button.getAttribute("data-journal-id") || "";
  const result = await loadAccountingVoucherDetail(journalId);
  renderJson(apiOutput, { accounting_voucher_detail: result });
  if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else {
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function openMandirTrialBalanceLedger(button) {
  const accountId = button.getAttribute("data-account-id") || "";
  if (!accountId) {
    mandirReportState.ledger = { ok: false, payload: { detail: "This Trial Balance row does not include an account reference." } };
    await loadMandirDashboard();
    return;
  }
  const accountLabel = button.closest("tr")?.querySelector("td:nth-child(2)")?.textContent?.trim() || accountId;
  mandirReportState.ledger = { loading: true, account_label: accountLabel };
  await loadMandirDashboard();
  document.getElementById("mandir-ledger-trace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const query = buildQueryString({
    from_date: accountingDrilldownState.from_date,
    to_date: accountingDrilldownState.to_date,
  });
  const result = await apiRequest(
    "mandirmitra",
    `/api/v1/journal-entries/reports/ledger/${encodeURIComponent(accountId)}?${query}`,
    { method: "GET" }
  );
  mandirReportState.ledger = result.ok ? result.payload : result;
  renderJson(apiOutput, { mandir_trial_balance_ledger: result });
  await loadMandirDashboard();
  document.getElementById("mandir-ledger-trace")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function approveOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const confirmed = window.confirm(`Approve onboarding request ${requestId}?`);
  if (!confirmed) {
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderJson(apiOutput, { approve_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}

async function rejectOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const reason = String(window.prompt(`Reason for rejecting ${requestId}`) || "").trim();
  if (reason.length < 3) {
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  renderJson(apiOutput, { reject_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — dialogs: drilldown / verification / rejection / cancel
// NOTE  : openMandirVerificationDialog, openMandirCancelReceiptDialog, drillAccountingReport
// ══════════════════════════════════════════════════════════════════════

function openTenantEntitlementsDialog(button) {
  const tenantId = button.getAttribute("data-tenant-id") || "";
  if (!tenantId) {
    return;
  }
  const tenantLabel = button.getAttribute("data-tenant-label") || tenantId;
  const currentStatus = button.getAttribute("data-tenant-status") || "active";
  const organizationType = button.getAttribute("data-organization-type") || "";
  const currentPlan = button.getAttribute("data-subscription-plan") || "free";
  const currentModules = new Set(
    String(button.getAttribute("data-enabled-modules") || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  );
  const availableModules = entitlementModulesByOrgType[organizationType] || Array.from(currentModules);

  entitlementTenantId.value = tenantId;
  entitlementTenantLabel.textContent = `${tenantLabel} (${organizationType || "tenant"})`;
  entitlementPlan.value = currentPlan;
  entitlementStatus.value = currentStatus;
  entitlementStatus.dataset.currentStatus = currentStatus;
  const hrAddonAvailable = button.getAttribute("data-hr-addon-available") === "1";
  // Show the HR add-on provisioning toggle only for MitraBooks (business) tenants.
  const isBusiness = String(organizationType || "").toUpperCase() === "BUSINESS";
  const hrToggle = isBusiness ? `
    <label class="checkbox-option" style="margin-top:10px;border-top:1px solid var(--border,#333);padding-top:10px;">
      <input type="checkbox" id="entitlement-hr-addon" ${hrAddonAvailable ? "checked" : ""}>
      <span><strong>HR &amp; Payroll add-on</strong> (enterprise) — provision for this tenant</span>
    </label>` : "";
  entitlementModules.innerHTML = availableModules.map((moduleKey) => `
    <label class="checkbox-option">
      <input type="checkbox" value="${escapeHtml(moduleKey)}" ${currentModules.has(moduleKey) ? "checked" : ""}>
      <span>${escapeHtml(moduleKey)}</span>
    </label>
  `).join("") + hrToggle;
  entitlementModules.dataset.hrInitial = hrAddonAvailable ? "1" : "0";

  entitlementDialog.showModal();
}

async function submitTenantEntitlements() {
  const tenantId = entitlementTenantId.value;
  const subscriptionPlan = entitlementPlan.value;
  const tenantStatus = entitlementStatus.value;
  const currentTenantStatus = entitlementStatus.dataset.currentStatus || "active";
  const enabledModules = Array.from(entitlementModules.querySelectorAll("input:checked"))
    .map((input) => input.value)
    .filter(Boolean);
  if (!tenantId || enabledModules.length === 0) {
    return;
  }
  const statusResult = tenantStatus === currentTenantStatus ? null : await apiRequest(
    APP_KEY,
    `/api/v1/tenants/${encodeURIComponent(tenantId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status: tenantStatus }),
    }
  );
  if (statusResult && !statusResult.ok) {
    renderJson(apiOutput, { update_tenant_status: statusResult });
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/tenants/${encodeURIComponent(tenantId)}/entitlements`, {
    method: "PATCH",
    body: JSON.stringify({
      subscription_plan: subscriptionPlan,
      enabled_modules: enabledModules,
    }),
  });

  // Provision / revoke the HR add-on if its toggle changed (super_admin only).
  let hrResult = null;
  const hrCheckbox = document.getElementById("entitlement-hr-addon");
  if (hrCheckbox) {
    const hrWanted = !!hrCheckbox.checked;
    const hrInitial = entitlementModules.dataset.hrInitial === "1";
    if (hrWanted !== hrInitial) {
      hrResult = await apiRequest(APP_KEY, `/api/v1/platform-owner/tenants/${encodeURIComponent(tenantId)}/hr-addon`, {
        method: "PUT",
        body: JSON.stringify({ available: hrWanted }),
      });
    }
  }

  renderJson(apiOutput, { update_tenant_status: statusResult, update_tenant_entitlements: result, hr_addon: hrResult });
  entitlementDialog.close();
  await loadPlatformOwnerDashboard();
}

async function setPlatformWorkspace(workspace) {
  currentExperience = "platform";
  activePlatformWorkspace = workspace || "dashboard";
  syncPlatformNavActiveState();
  dashboardPreview.innerHTML = renderPlatformDashboard(lastPlatformOwnerDashboard || emptyPlatformDashboardPayload());
  await loadPlatformOwnerDashboard();
}

function setExperience(nextExperience) {
  currentExperience = nextExperience;
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${nextExperience}`)?.classList.add("active");
  if (nextExperience === "platform") {
    activePlatformWorkspace = "dashboard";
  }
  renderModules();
  if (nextExperience === "platform") {
    loadPlatformOwnerDashboard();
  } else if (nextExperience === "mandir") {
    loadMandirDashboard();
  } else if (nextExperience === "gruha") {
    loadGruhaDashboard();
  } else if (nextExperience === "mitrabooks") {
    const appKey = EXPERIENCE_APP_KEYS[nextExperience] || APP_KEY;
    loadAndRenderGroupedNav(appKey);
    loadAccountingDrilldownResult().then(() => {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
    });
  }
}

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  lastModuleContext = null;
  updateSessionUi();
  runChecks();
});

// Enhanced login form handling
const loginForm = document.getElementById("login-form");
if (loginForm) {
  let _loginInProgress = false;
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (_loginInProgress) return;
    _loginInProgress = true;
    try {
      await signInWithPassword();
    } finally {
      _loginInProgress = false;
    }
  });
}

// Password visibility toggle
const togglePasswordBtn = document.getElementById("toggle-password");
if (togglePasswordBtn && loginPassword) {
  togglePasswordBtn.addEventListener("click", (event) => {
    event.preventDefault();
    const nextType = loginPassword.type === "password" ? "text" : "password";
    loginPassword.type = nextType;
    const isVisible = nextType === "text";
    togglePasswordBtn.classList.toggle("show", isVisible);
    togglePasswordBtn.setAttribute("aria-pressed", String(isVisible));
  });
}
document.getElementById("run-checks").addEventListener("click", runChecks);
document.getElementById("clear-token").addEventListener("click", () => {
  signOutAndReturnToLogin();
});

document.getElementById("forgot-password-open")?.addEventListener("click", () => {
  if (forgotPasswordEmail && loginEmail?.value) {
    forgotPasswordEmail.value = loginEmail.value;
  }
  clearAuthFieldMessage("forgot-error-field");
  setAuthPanelMode("forgot");
  setLoginStatus("", "", "");
});
document.getElementById("forgot-password-back")?.addEventListener("click", () => {
  setAuthPanelMode("login");
  setLoginStatus("", "", "");
});
document.getElementById("reset-password-back")?.addEventListener("click", () => {
  pendingPasswordResetToken = "";
  if (window.history?.replaceState) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  setAuthPanelMode("login");
  setLoginStatus("", "", "");
});
forgotPasswordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await requestPasswordReset();
});
resetPasswordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await completePasswordReset();
});
if (pendingPasswordResetToken) {
  setAuthPanelMode("reset");
  setLoginStatus("warn", "Reset link opened", "Enter a new password to complete the reset.");
} else {
  setAuthPanelMode("login");
}

// Fired by api-client when silent token refresh fails — show clean login screen
window.addEventListener("auth-session-expired", () => {
  lastModuleContext = null;
  lastBusinessAccounts = [];
  lastBusinessParties = [];
  lastBusinessVouchers = [];
  lastVoucherApprovalQueue = [];
  lastAccountingDrilldown = null;
  clearAllTokens();
  if (loginPassword) loginPassword.value = "";
  dashboardPreview.innerHTML = "";
  renderModules();
  updateSessionUi();
  setLoginStatus("warn", "Session expired", "Your session has expired. Please sign in again.");
});
document.getElementById("topbar-logout")?.addEventListener("click", () => {
  signOutAndReturnToLogin();
});
document.getElementById("sidebar-logout")?.addEventListener("click", () => {
  signOutAndReturnToLogin();
});
accountMenuTrigger?.addEventListener("click", () => {
  const isOpen = accountMenuPanel && !accountMenuPanel.hidden;
  if (accountMenuPanel) {
    accountMenuPanel.hidden = isOpen;
  }
  accountMenuTrigger.setAttribute("aria-expanded", String(!isOpen));
});
document.getElementById("topbar-update-password")?.addEventListener("click", openPasswordDialog);
document.getElementById("change-password-close")?.addEventListener("click", () => passwordDialog?.close());
document.getElementById("change-password-cancel")?.addEventListener("click", () => passwordDialog?.close());
passwordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await updateCurrentPassword();
});
document.addEventListener("click", (event) => {
  if (!accountMenuPanel || accountMenuPanel.hidden) {
    return;
  }
  if (!event.target.closest(".account-menu")) {
    closeAccountMenu();
  }
});
nav.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-nav-group-toggle]");
  if (!toggle) {
    return;
  }
  event.preventDefault();
  const groupId = toggle.getAttribute("data-nav-group-toggle") || "";
  const panel = document.getElementById(groupId);
  const expanded = toggle.getAttribute("aria-expanded") !== "false";
  toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
  if (panel) {
    panel.hidden = expanded;
  }
});
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-mandir-workspace]");
  if (!link || currentExperience !== "mandir") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setMandirWorkspace(link.dataset.mandirWorkspace || "overview");
});
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-gruha-workspace]");
  if (!link || currentExperience !== "gruha") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setGruhaWorkspace(link.dataset.gruhaWorkspace || "overview");
});
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-business-workspace]");
  if (!link || currentExperience !== "mitrabooks") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setBusinessWorkspace(link.dataset.businessWorkspace || "overview");
});

// ══════════════════════════════════════════════════════════════════════

// Wire widget system deps (avoids modules/widgets.js importing app.js)
initWidgets({
  escapeHtml,
  getExperience: () => currentExperience,
  getWorkspace: () => activeBusinessWorkspace,
  renderExecutiveDashboard: () => renderBusinessExecutiveDashboard(),
});

// Wire HR workspace deps (avoids modules/workspaces/hr.js importing app.js)
initHrWorkspace({
  escapeHtml,
  refreshHrView: () => {
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "hr") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  },
});
// Wire Mandir financial report renderers (avoids import cycle with app.js)
initMandirFinancialReports({
  escapeHtml,
  formatCurrency,
  renderStatCards,
  getDrilldownFromDate: () => accountingDrilldownState.from_date,
  getDrilldownToDate: () => accountingDrilldownState.to_date,
  todayIsoDate,
});
// Wire Mandir table renderers (avoids import cycle with app.js)
initMandirTables({
  escapeHtml,
  formatCurrency,
});
// Wire GST returns cluster (avoids import cycle with app.js)
initGstReturns({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  reportUnavailablePanel,
  todayIsoDate,
  currentFinancialYear,
  currentFyQuarter,
  recentFinancialYears,
  recentFyQuarters,
  getApiOutput: () => apiOutput,
});
// Wire sales invoices workspace (avoids import cycle with app.js)
initSalesInvoices({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  tdsSectionOptions,
  tdsSectionRate,
  loadTdsSections,
  isBusinessAdmin,
  reversalPanel,
  focusBusinessEntryField,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getLastBusinessParties: () => lastBusinessParties,
  loadBusinessParties,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  businessAccountsForSelection,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getLastInventoryItems: () => lastInventoryItems,
  loadInventoryItems,
  inventoryItemOptions,
  renderEinvoiceSection,
  loadEinvoiceView,
  clearEinvoiceView,
  renderBusinessAttachmentPanel,
  listBusinessAttachments,
  getApiOutput: () => apiOutput,
  hasTdsSectionsCache: () => !!tdsSectionsCache,
});

// Wire purchase bills workspace (avoids import cycle with app.js)
initPurchaseBills({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  tdsSectionOptions,
  tdsSectionRate,
  loadTdsSections,
  isBusinessAdmin,
  reversalPanel,
  focusBusinessEntryField,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getLastBusinessParties: () => lastBusinessParties,
  loadBusinessParties,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  businessAccountsForSelection,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getLastInventoryItems: () => lastInventoryItems,
  loadInventoryItems,
  inventoryItemOptions,
  renderBusinessAttachmentPanel,
  listBusinessAttachments,
  getApiOutput: () => apiOutput,
  hasTdsSectionsCache: () => !!tdsSectionsCache,
});

// Wire credit notes workspace (avoids import cycle with app.js)
initCreditNotes({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  reversalPanel,
  focusBusinessEntryField,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getLastBusinessParties: () => lastBusinessParties,
  loadBusinessParties,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getApiOutput: () => apiOutput,
});

// Wire debit notes workspace (avoids import cycle with app.js)
initDebitNotes({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  reversalPanel,
  focusBusinessEntryField,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getLastBusinessParties: () => lastBusinessParties,
  loadBusinessParties,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getApiOutput: () => apiOutput,
});

// Wire workspace event handlers (avoids import cycle with app.js)
initEventHandlers({
  get activeReceiptPreviewObjectUrl() { return activeReceiptPreviewObjectUrl; },
  set activeReceiptPreviewObjectUrl(v) { activeReceiptPreviewObjectUrl = v; },
  get activeSettingsDetailId() { return activeSettingsDetailId; },
  set activeSettingsDetailId(v) { activeSettingsDetailId = v; },
  addBillLine,
  addCnLine,
  addDnLine,
  addInvoiceLine,
  addVoucherLine,
  apiRequest,
  applyAccountingDrilldownFilters,
  applyAuditFilters,
  applyBusinessListFilter,
  applyBusinessReportFilter,
  applyFifoSuggestion,
  applyMandirListFilter,
  approveOnboardingRequest,
  businessAttachmentPath,
  get caClientDraft() { return caClientDraft; },
  set caClientDraft(v) { caClientDraft = v; },
  caDocumentAttachmentState,
  get caInviteError() { return caInviteError; },
  set caInviteError(v) { caInviteError = v; },
  get caInviteSuccess() { return caInviteSuccess; },
  set caInviteSuccess(v) { caInviteSuccess = v; },
  get caPracticeFilters() { return caPracticeFilters; },
  set caPracticeFilters(v) { caPracticeFilters = v; },
  cancelBill,
  cancelCreditNote,
  cancelDebitNote,
  cancelInvoice,
  closeReceiptPreview,
  coaEnterEditMode,
  coaExitEditMode,
  coaHandleAddSubmit,
  coaHandleSaveName,
  get coaTypeFilter() { return coaTypeFilter; },
  set coaTypeFilter(v) { coaTypeFilter = v; },
  confirmBankReconMatch,
  copyDunningLetter,
  createBusinessParty,
  createBusinessVoucherByType,
  createCaClient,
  createCaPracticeDocument,
  createDimensionFromForm,
  createFixedAssetFromForm,
  createInventoryItemFromForm,
  createStockMovementFromForm,
  creditUi,
  dashboardPreview,
  deactivateBusinessParty,
  deactivateDimension,
  deactivateInventoryItem,
  debitUi,
  disposeFixedAsset,
  downloadApiFile,
  downloadBusinessReport,
  downloadCmp08Json,
  downloadCreditNoteJson,
  downloadDebitNoteJson,
  downloadDimensionReport,
  downloadGstr1Json,
  downloadGstr3bJson,
  downloadGstr4Json,
  downloadInv01Json,
  downloadInvoicePdf,
  downloadMandirReceipt,
  downloadObExport,
  downloadObTemplate,
  downloadTallyXmlExport,
  downloadViTemplate,
  drillAccountingReport,
  entitlementDialog,
  entitlementForm,
  get faFormOpen() { return faFormOpen; },
  set faFormOpen(v) { setFaFormOpen(v); },
  gstReturnState,
  handleVoucherDialogKeyboard,
  hrAllocateLeave,
  hrApplyLeave,
  hrAssignSalary,
  hrCreateDeclaration,
  hrCreateEmployee,
  hrCreateFnf,
  hrCreateLeaveType,
  hrCreateStructure,
  hrDecideLeave,
  hrDownloadFnfPdf,
  hrDownloadJoiningLetter,
  hrDownloadLetter,
  hrDownloadSlipPdf,
  hrEnable,
  hrMarkDeclined,
  hrMarkJoined,
  hrRunPayroll,
  hrSaveLetterSettings,
  hrTransitionFnf,
  hrUi,
  hrVerifyDeclaration,
  loadBankReconciliation,
  loadBillAttachments,
  loadBranchConsolidatedReport,
  loadBusinessGeneralLedger,
  loadBusinessReportLedgerFromSelect,
  loadCaAccessUsers,
  loadCaClients,
  loadCaDocumentAttachments,
  loadCaPracticeDocuments,
  loadDimensionReport,
  loadFinancialHealth,
  loadHrFnf,
  loadHrLeave,
  loadHrRunSlips,
  loadHrTax,
  loadHrWorkspace,
  loadMfgPl,
  loadMfgWorkspace,
  loadPartyStatement,
  loadStockMovements,
  loadStockRegister,
  loadVoucherApprovalQueue,
  lockGstPeriodFromInput,
  mandirCancelReceiptDialog,
  mandirCancelReceiptForm,
  mandirCorrectionDialog,
  mandirCorrectionForm,
  mandirRejectionDialog,
  mandirRejectionForm,
  mandirVerificationDialog,
  mandirVerificationForm,
  markBillPaidFull,
  mfgAddBomComponent,
  mfgAddWoActual,
  get mfgBudgetVsActual() { return mfgBudgetVsActual; },
  set mfgBudgetVsActual(v) { mfgBudgetVsActual = v; },
  get mfgCompleteFor() { return mfgCompleteFor; },
  set mfgCompleteFor(v) { mfgCompleteFor = v; },
  mfgCompleteWorkOrder,
  mfgCreateBom,
  mfgCreateBudget,
  mfgCreateCostCentre,
  mfgCreateWorkOrder,
  mfgEnableLayer,
  get mfgError() { return mfgError; },
  set mfgError(v) { mfgError = v; },
  mfgOpenComplete,
  mfgPl,
  get mfgPlFrom() { return mfgPlFrom; },
  set mfgPlFrom(v) { mfgPlFrom = v; },
  get mfgPlTo() { return mfgPlTo; },
  set mfgPlTo(v) { mfgPlTo = v; },
  mfgRemoveBomComponent,
  mfgRemoveWoActual,
  mfgSetBudgetStatus,
  mfgSetWorkOrderStatus,
  get mfgTab() { return mfgTab; },
  set mfgTab(v) { mfgTab = v; },
  mfgViewBudgetVsActual,
  get mfgWoActualDraft() { return mfgWoActualDraft; },
  set mfgWoActualDraft(v) { mfgWoActualDraft = v; },
  nav,
  openAccountingVoucherDetail,
  openAuditEventDetailDialog,
  openBillCreate,
  openBillDetail,
  openBusinessCreatePartyDialog,
  openBusinessCreateVoucherDialog,
  openBusinessEditPartyDialog,
  openCreditNoteCreate,
  openCreditNoteDetail,
  openDebitNoteCreate,
  openDebitNoteDetail,
  openInvoiceCreate,
  openInvoiceDetail,
  openInvoiceSettings,
  openMandirCancelReceiptDialog,
  openMandirCorrectionDialog,
  openMandirRejectionDialog,
  openMandirTrialBalanceLedger,
  openMandirVerificationDialog,
  openTenantEntitlementsDialog,
  openWidgetSettings,
  pageAuditList,
  pageBusinessList,
  pageMandirList,
  postBankReconStatementVoucher,
  postBulkVouchers,
  postClosingStock,
  postCmp08Liability,
  postDepreciationRun,
  postGstSettlement,
  postOpeningBalances,
  postYearEndClose,
  previewBulkVouchers,
  previewCmp08FromInput,
  previewDepreciation,
  previewGstSettlementFromInput,
  previewGstr1FromInput,
  previewGstr3bFromInput,
  previewGstr4FromInput,
  previewItcReversalsFromInput,
  previewMandirReceipt,
  previewOpeningBalances,
  previewTdsRegisterFromInput,
  previewYearEnd,
  printBusinessReport,
  printCreditNoteDetail,
  printDebitNoteDetail,
  purchaseUi,
  receiptPreviewDialog,
  receiptPreviewFrame,
  reclaimItcForBill,
  reconcileGstr2b,
  recordDunningSent,
  recordEinvoiceIrn,
  refreshCurrentBusinessReport,
  rejectOnboardingRequest,
  removeBillLine,
  removeCnLine,
  removeDnLine,
  removeInvoiceLine,
  removeVoucherLine,
  renderBusinessWorkspace,
  rerenderBusinessReportsIfActive,
  rerenderCreditNoteIfActive,
  rerenderDebitNoteIfActive,
  rerenderPurchaseIfActive,
  rerenderSalesIfActive,
  resetAccountingDrilldown,
  resetAuditFilters,
  resetBusinessListFilter,
  resetMandirListFilter,
  reverseBankReconMatch,
  reverseBusinessVoucher,
  reverseItcForBill,
  reviewBusinessVoucher,
  salesUi,
  saveBusinessAdminSettingsSection,
  saveInvoiceSettings,
  selectAllocationPayment,
  setAgingKind,
  setAllocationKind,
  setBusinessPurchaseView,
  setBusinessReportTab,
  setBusinessSalesView,
  setBusinessWorkspace,
  setCreditNoteView,
  setDebitNoteView,
  setExperience,
  setGruhaWorkspace,
  setGstPeriodLock,
  setLoginStatus,
  setMandirWorkspace,
  setPlatformWorkspace,
  statusDetailText,
  submitAllocation,
  submitBill,
  submitCreditNote,
  submitDebitNote,
  submitInvoice,
  submitMandirCancelReceipt,
  submitMandirComplianceForm,
  submitMandirCreateForm,
  submitMandirPublicPaymentCorrection,
  submitMandirPublicPaymentRejection,
  submitMandirPublicPaymentVerification,
  submitTenantEntitlements,
  toggleWidgetCollapse,
  updateBillTotalsDisplay,
  updateBusinessParty,
  updateCaPracticeDocumentStatus,
  updateCnTotalsDisplay,
  updateDnTotalsDisplay,
  updateInvoiceTotalsDisplay,
  updateVoucherTypeForm,
  uploadBankStatementFile,
  uploadBusinessAttachmentFiles,
});

// Initialize theme on app load
initializeTheme();

// Wire shell UI (theme toggles, sidebar org/FY, quick actions)
initShellUi({
  get activeBusinessWorkspace() { return activeBusinessWorkspace; },
  set activeBusinessWorkspace(v) { activeBusinessWorkspace = v; },
  addBillLine,
  addCnLine,
  addDnLine,
  addInvoiceLine,
  creditUi,
  currentExperience,
  dashboardPreview,
  debitUi,
  experienceConfig,
  hasTrustedSession,
  get lastCaDocuments() { return lastCaDocuments; },
  set lastCaDocuments(v) { lastCaDocuments = v; },
  get lastCaDocumentsResult() { return lastCaDocumentsResult; },
  set lastCaDocumentsResult(v) { lastCaDocumentsResult = v; },
  loadBusinessDashboardStats,
  loadCaPracticeDocuments,
  openBillCreate,
  openBusinessCreatePartyDialog,
  openBusinessCreateVoucherDialog,
  openCreditNoteCreate,
  openDebitNoteCreate,
  openInvoiceCreate,
  orgSelectorMeta,
  purchaseUi,
  renderBusinessWorkspace,
  renderDashboardPreview,
  salesUi,
  get selectedOrgType() { return selectedOrgType; },
  set selectedOrgType(v) { selectedOrgType = v; },
  setLoginStatus,
  setTheme,
  submitBill,
  submitCreditNote,
  submitDebitNote,
  submitInvoice,
  syncBusinessNavActiveState,
  syncOrgSelectorOptions,
  updateTrustedContextUi,
});

// Wire accounting dimensions (avoids import cycle with app.js)
initDimensions({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  downloadApiFile,
  getApiOutput: () => apiOutput,
});

// Wire fixed assets + depreciation (avoids import cycle with app.js)
initFixedAssets({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  businessAccountsForSelection,
  bankAccountOptions,
  isBusinessAdmin,
  recentFinancialYears,
  currentFinancialYear,
  getApiOutput: () => apiOutput,
});

// Wire inventory workspace (avoids import cycle with app.js)
initInventory({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  getApiOutput: () => apiOutput,
});

// Wire bank reconciliation + cash book (avoids import cycle with app.js)
initBankRecon({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  businessAccountsForSelection,
  renderStatCards,
  getBusinessReportState: () => businessReportState,
  getApiOutput: () => apiOutput,
});

// Wire customer statements + dunning (avoids import cycle with app.js)
initStatements({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  getLastBusinessParties: () => lastBusinessParties,
  getApiOutput: () => apiOutput,
});

// Wire e-invoicing (avoids import cycle with app.js / sales-invoices)
initEinvoice({
  escapeHtml,
  setLoginStatus,
  statusDetailText,
  rerenderSalesIfActive,
  getApiOutput: () => apiOutput,
});

// Wire TDS/TCS register (avoids import cycle with app.js)
initTds({
  escapeHtml,
  formatCurrency,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  recentFyQuarters,
  currentFyQuarter,
  getApiOutput: () => apiOutput,
});

// Wire ITC reversals / reclaim (avoids import cycle with app.js)
initItcReversals({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  todayIsoDate,
  getApiOutput: () => apiOutput,
});

// Wire GST period locks (avoids import cycle with app.js)
initPeriodLocks({
  escapeHtml,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  todayIsoDate,
  getApiOutput: () => apiOutput,
});

// Wire opening balances / bulk vouchers / year-end (avoids import cycle with app.js)
initOpeningYearEnd({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  recentFinancialYears,
  currentFinancialYear,
  downloadApiFile,
  getApiOutput: () => apiOutput,
});

// Wire payment allocation + AR/AP aging (avoids import cycle with app.js)
initPaymentAllocation({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  reportResultPayload,
  getBusinessReportState: () => businessReportState,
  getApiOutput: () => apiOutput,
});

// Wire audit trail (avoids import cycle with app.js)
initAuditTrail({
  escapeHtml,
  setLoginStatus,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
});

// Wire GruhaMitra workspace (avoids import cycle with app.js)
initGruhamitra({
  escapeHtml,
  formatCurrency,
  resultRows,
  resultPayload,
  renderStatCards,
  renderStatusBlock,
  renderSimpleTable,
  renderActivity,
  renderAccountingDrilldownPanel,
  gruhaNavigationItems,
  currentBillingPeriodQuery,
  loadAccountingDrilldownResult,
  renderDashboardPreview,
  syncGruhaNavActiveState,
  getExperienceConfig: () => experienceConfig,
  getDashboardPreview: () => dashboardPreview,
  getApiOutput: () => apiOutput,
});

// Wire core financial reports (avoids import cycle with app.js)
initFinancialReports({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  reportUnavailablePanel,
  reportResultPayload,
  rerenderBusinessReportsIfActive,
  refreshCurrentBusinessReport,
  findBusinessAccountById,
  accountRowsFromPayload,
  businessAccountsForSelection,
  renderStatCards,
  isBusinessReportTab: (tab) => BUSINESS_REPORT_TABS.some((t) => t.id === tab),
  setBankCashBookType,
  getBankCashBookType: () => bankCashBookType,
  getBusinessReportState: () => businessReportState,
  getApiOutput: () => apiOutput,
});

// HEADER & HEALTH WIDGET (Phase 1C Step 7)
// ============================================

/**
 * Update health widget with data
 * @param {number} percentage - Health percentage (0-100)
 * @param {string} status - Status message
 */

// ══════════════════════════════════════════════════════════════════════
// SECTION: BOOKS HEALTH WIDGET
// NOTE  : updateHealthWidget / refreshBooksHealthWidget / initializeHealthWidget
// ══════════════════════════════════════════════════════════════════════

function updateHealthWidget(percentage = null, status = "Run checks", tone = "pending") {
  const widget = document.getElementById("books-health-widget");
  const healthPercent = document.getElementById("health-percent-text");
  const healthBar = document.getElementById("health-circle-bar");
  const healthStatus = document.querySelector(".health-text span");
  const safePercentage = Number.isFinite(Number(percentage))
    ? Math.max(0, Math.min(100, Number(percentage)))
    : null;

  if (widget) {
    widget.classList.remove("pending", "warn", "ok");
    widget.classList.add(tone);
  }
  if (healthPercent) {
    healthPercent.textContent = safePercentage === null ? "--" : `${safePercentage}%`;
  }
  if (healthBar) {
    const dasharray = `${safePercentage ?? 0}, 100`;
    healthBar.setAttribute("stroke-dasharray", dasharray);
  }
  if (healthStatus) {
    healthStatus.textContent = status;
  }
}

function refreshBooksHealthWidget() {
  if (!lastModuleContext) {
    updateHealthWidget(null, "Run checks", "pending");
    return;
  }

  const { healthState } = getBusinessHealthState();
  const checks = [
    healthState.isBusinessTenant,
    healthState.hasBusinessModule,
    healthState.hasAccountingModule,
    healthState.accountsLoaded,
    healthState.hasCashBank,
    healthState.hasRevenue,
    healthState.hasExpense,
    healthState.partiesGstinReady,
    healthState.drilldownReady,
  ];
  const passed = checks.filter(Boolean).length;
  const percentage = Math.round((passed / checks.length) * 100);
  const ready = passed === checks.length;
  const blocked = healthState.accountsBlocked || healthState.partiesBlocked;
  updateHealthWidget(
    percentage,
    ready ? "Ready" : blocked ? "Needs review" : "In progress",
    ready ? "ok" : "warn"
  );
}

function updatePageHeader(parentName = "Workspaces", currentName = "Dashboard", pageTitle = "Dashboard Workspace") {
  const breadcrumbParent = document.getElementById("breadcrumb-parent");
  const breadcrumbCurrent = document.getElementById("breadcrumb-current");
  const viewTitle = document.getElementById("view-title");

  if (breadcrumbParent) breadcrumbParent.textContent = parentName;
  if (breadcrumbCurrent) breadcrumbCurrent.textContent = currentName;
  if (viewTitle) viewTitle.textContent = pageTitle;
}

/**
 * Initialize health widget on page load
 */
function initializeHealthWidget() {
  refreshBooksHealthWidget();
}

/**
 * Initialize header on page load
 */
function initializeHeader() {
  updatePageHeader("Workspaces", "Dashboard", "Dashboard Workspace");
  initializeHealthWidget();
}

// Call on app initialization
initializeHeader();

if (isProductionShell()) {
  const configuredApiBase = getConfiguredApiBaseUrl();
  const currentOrigin = String(window.location.origin || "").replace(/\/+$/, "");
  const pointsAtFrontend = configuredApiBase === currentOrigin
    || /mitrabooks-erp\.vercel\.app|mandirmitra\.sanmitratech\.in|gruhamitra\.sanmitratech\.in/i.test(configuredApiBase);
  if (!configuredApiBase || pointsAtFrontend) {
    setConfiguredApiBaseUrl(DEFAULT_DEPLOYED_API_BASE_URL);
  }
}
apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
document.getElementById(`mode-${currentExperience}`)?.classList.add("active");
updateSessionUi();
renderModules();

// Load grouped navigation for MitraBooks if already signed in (Phase 1D)
if (currentExperience === "mitrabooks" && getAccessToken()) {
  const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  loadAndRenderGroupedNav(appKey).catch(err => {
    console.error("[Init] Failed to load grouped nav on page load:", err);
  });
}

renderModuleState(moduleState);
document.documentElement.dataset.mitrabooksShellHandlersReady = "1";
void (async () => {
  try {
    await runChecks();
  } finally {
    document.documentElement.dataset.mitrabooksShellReady = "1";
  }
})();

