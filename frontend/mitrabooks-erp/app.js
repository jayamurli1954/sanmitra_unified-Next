
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
  bankReconAccountId,
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

import {
  initBusinessReportsHub,
  reportResultPayload,
  refreshCurrentBusinessReport,
  rerenderBusinessReportsIfActive,
  reportExportToolbar,
  businessReportExports,
  downloadBusinessReport,
  downloadTallyXmlExport,
  printBusinessReport,
  downloadJsonObject,
  printBusinessDocumentDetail,
  downloadCreditNoteJson,
  downloadDebitNoteJson,
  printCreditNoteDetail,
  printDebitNoteDetail,
  renderBusinessReportsWorkspace,
  reportUnavailablePanel,
} from "./modules/workspaces/business-reports-hub.js";

import {
  initAuthSession,
  hasTrustedSession,
  updateSessionUi,
  compactAccountLabel,
  signOutAndReturnToLogin,
  closeAccountMenu,
  openPasswordDialog,
  loadCurrentUserProfile,
  completeWorkspaceSignIn,
  updateCurrentPassword,
  activeOrgSelectorType,
  syncOrgSelectorOptions,
  updateTrustedContextUi,
  signInWithPassword,
} from "./modules/workspaces/auth-session.js";

import {
  initBusinessWorkspace,
  renderBusinessWorkspace,
  setBusinessWorkspace,
  syncBusinessNavActiveState,
} from "./modules/workspaces/business-workspace.js";

import {
  initDashboardPreviewShell,
  renderRecentTenantsTable,
  renderPlatformRecentOnboardingTable,
  renderPlatformSubscriptionsTable,
  emptyPlatformDashboardPayload,
  renderPlatformDashboard,
  renderDashboardPreview,
} from "./modules/workspaces/dashboard-preview-shell.js";

import {
  initNavigationShell,
  renderModules,
  mandirNavigationItems,
  gruhaNavigationItems,
  platformNavigationItems,
  legacyBusinessNavigationItems,
  loadAndRenderGroupedNav,
  renderGroupedNav,
  renderGroupedNavFromItems,
} from "./modules/workspaces/navigation-shell.js";

import {
  isMandirHost,
  isGruhaHost,
  isProductionShell,
  initialExperience,
  entitlementModulesByOrgType,
  orgSelectorMeta,
  experienceConfig,
} from "./modules/workspaces/experience-config.js";

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

import {
  initVouchers,
  lastBusinessVouchers,
  lastVoucherApprovalQueue,
  clearVoucherListState,
  setLastBusinessVouchers,
  setLastVoucherApprovalQueue,
  loadBusinessVouchers,
  loadVoucherApprovalQueue,
  reviewBusinessVoucher,
  reverseBusinessVoucher,
  renderVoucherTypeForm,
  updateVoucherTypeForm,
  focusFirstVoucherField,
  submitVoucherDialogFromKeyboard,
  handleVoucherDialogKeyboard,
  openBusinessCreateVoucherDialog,
} from "./modules/workspaces/vouchers.js";

import {
  initVoucherCreate,
  loadVoucherPartyOutstanding,
  createBusinessVoucherByType,
  createSimplePartyVoucher,
  createContraVoucher,
  createJournalVoucher,
  createBusinessVoucher,
} from "./modules/workspaces/voucher-create.js";

import {
  initParties,
  lastBusinessParties,
  lastBusinessPartiesResult,
  setLastBusinessParties,
  setLastBusinessPartiesResult,
  clearPartiesState,
  loadBusinessParties,
  createBusinessParty,
  updateBusinessParty,
  deactivateBusinessParty,
  openBusinessCreatePartyDialog,
  openBusinessEditPartyDialog,
} from "./modules/workspaces/parties.js";

import {
  initCoa,
  coaTypeFilter,
  setCoaTypeFilter,
  renderBusinessCoaWorkspace,
  coaHandleAddSubmit,
  coaHandleSaveName,
  coaEnterEditMode,
  coaExitEditMode,
} from "./modules/workspaces/coa.js";

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
  setLastCaDocuments,
  setLastCaDocumentsResult,
  loadCaPracticeDocuments,
  loadCaClients,
  rerenderCaPracticeIfActive,
  loadCaAccessUsers,
  createCaPracticeDocument,
  createCaClient,
  loadCaDocumentAttachments,
  caClientById,
  renderCaDocumentIntake,
  renderCaPracticePortalWorkspace,
  updateCaPracticeDocumentStatus,
} from "./modules/workspaces/ca-practice.js";

import {
  initFinancialHealth,
  lastFinancialHealth,
  financialHealthLoadInFlight,
  setLastFinancialHealth,
  resetFinancialHealthState,
  renderFinancialHealthWorkspace,
  loadFinancialHealth,
} from "./modules/workspaces/financial-health.js";

import {
  initAccountingDrilldown,
  accountingDrilldownState,
  lastAccountingDrilldown,
  lastAccountingVoucherDetail,
  setLastAccountingDrilldown,
  setLastAccountingVoucherDetail,
  setAccountingDrilldownState,
  accountingDrilldownTitle,
  renderAccountingDrilldownRows,
  renderAccountingVoucherDetail,
  renderAccountingDrilldownPanel,
  accountingDrilldownPath,
  loadAccountingDrilldownResult,
  loadAccountingVoucherDetail,
  readAccountingDrilldownFilterValues,
  refreshCurrentAccountingDrilldown,
  applyAccountingDrilldownFilters,
  resetAccountingDrilldown,
  drillAccountingReport,
  openAccountingVoucherDetail,
} from "./modules/workspaces/accounting-drilldown.js";

import {
  initVoucherForm,
  voucherLineCounter,
  setVoucherLineCounter,
  syncVoucherAccountFromText,
  renderVoucherLineItem,
  updateVoucherBalance,
  updateVoucherBalanceState,
  addVoucherLine,
  removeVoucherLine,
  clearVoucherForm,
} from "./modules/workspaces/voucher-form.js";

import {
  initAccountLoading,
  lastBusinessAccounts,
  lastBusinessAccountsResult,
  lastBusinessDashboardStats,
  lastBusinessMisKpis,
  lastBusinessDataHealth,
  businessDashboardLoadInFlight,
  businessMisLoadInFlight,
  businessDataHealthLoadInFlight,
  setLastBusinessAccounts,
  loadBusinessAccounts,
  loadBusinessDashboardStats,
  loadBusinessMisKpis,
  loadBusinessDataHealth,
  filterBusinessAccountsByQuery,
} from "./modules/workspaces/account-loading.js";

import {
  initAccountSelector,
  renderAccountSelectorComponent,
  updateAccountSuggestions,
  selectAccountFromSuggestion,
  selectBusinessAccount,
  closeAllAccountSuggestions,
} from "./modules/workspaces/account-selector.js";

import {
  initAccountHelpers,
  normalizeBusinessAccount,
  businessAccountLabel,
  businessAccountsForSelection,
  hasLoadedBusinessAccounts,
  findBusinessAccountById,
  accountIdForVoucherPayload,
  populateVoucherAccountSelect,
  populateAccountPickerSelect,
  refreshVoucherAccountDatalist,
  updateVoucherAccountsStatus,
  refreshVoucherAccountSelects,
  accountRowsFromPayload,
  normalizedAccountRows,
  hasBusinessAccount,
  countPartiesMissingGstin,
  dataHealthItem,
  dataHealthAction,
  renderBusinessDataHealthIssueList,
  renderBusinessDataHealthActions,
  getBusinessHealthState,
  renderBusinessDataHealthPanel,
  updateHealthWidget,
  refreshBooksHealthWidget,
  initializeHealthWidget,
} from "./modules/workspaces/account-helpers.js";

import {
  initExecutiveDashboard,
  renderMisPartyRows,
  renderMisKpiContractPanel,
  renderBusinessExecutiveDashboard,
} from "./modules/workspaces/executive-dashboard.js";

import {
  initBusinessListTables,
  renderBusinessPartiesTable,
  renderBusinessPartiesListFilters,
  renderBusinessVouchersTable,
  renderBusinessVouchersListFilters,
  renderVoucherApprovalQueuePanel,
} from "./modules/workspaces/business-list-tables.js";

import {
  initAttachments,
  businessAttachmentPath,
  uploadBusinessAttachmentFiles,
  listBusinessAttachments,
  attachmentListSummary,
  renderBusinessAttachmentPanel,
} from "./modules/workspaces/attachments.js";

import {
  initSettingsWorkspace,
  activeSettingsDetailId,
  lastBusinessAdminSettings,
  setActiveSettingsDetailId,
  setLastBusinessAdminSettings,
  settingsItemId,
  allMitraBooksSettingsItems,
  findMitraBooksSettingsItem,
  businessAdminSettingsSectionKey,
  buildBusinessAdminSettingsPayload,
  settingsStatusClass,
  renderMitraBooksSettingsCard,
  renderBusinessAdminSettingsEditor,
  renderMitraBooksSettingsDetail,
  renderMitraBooksSettingsWorkspace,
  renderProfessionalSuiteWorkspace,
  loadBusinessAdminSettings,
  saveBusinessAdminSettingsSection,
} from "./modules/workspaces/settings-workspace.js";

import {
  initBusinessListFilters,
  businessListState,
  applyBusinessListFilter,
  resetBusinessListFilter,
  pageBusinessList,
} from "./modules/workspaces/business-list-filters.js";

import {
  currentFinancialYear,
  recentFinancialYears,
  currentFyQuarter,
  recentFyQuarters,
  financialYearStartIso,
} from "./modules/workspaces/fiscal-year.js";

import {
  initDashboardPrimitives,
  renderStatCards,
  renderActionTiles,
  renderActivity,
  renderBusinessRecentVoucherRows,
} from "./modules/workspaces/dashboard-primitives.js";

import {
  initMandirOperationalReports,
  panchangTimeRange,
  renderMandirPanchang,
  reportPayload,
  reportRows,
  renderMandirOperationalReports,
  renderMandirDevoteesView,
} from "./modules/workspaces/mandir-operational-reports.js";

import {
  initMandirDashboard,
  renderMandirDashboardHome,
  renderMandirDashboard,
  renderMandirSettings,
  renderMandirImplementationChecks,
  renderMandirPlatformOwnerShortcut,
} from "./modules/workspaces/mandir-dashboard.js";

import {
  initMandirDashboardLoaders,
  showMandirSplash,
  hideMandirSplash,
  loadMandirDashboard,
  openMandirTrialBalanceLedger,
} from "./modules/workspaces/mandir-dashboard-loaders.js";

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

// Experience detection + product shell config live in modules/workspaces/experience-config.js

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

// Navigation shell + module boot renderers live in modules/workspaces/navigation-shell.js

// Dashboard stat/activity primitives live in modules/workspaces/dashboard-primitives.js

// Shared business attachment helpers (invoices, bills, CA documents)

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

// Business executive dashboard lives in modules/workspaces/executive-dashboard.js

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

// Auth + session helpers live in modules/workspaces/auth-session.js

// ══════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════
// Shared money/count formatters (used across workspaces)
// ══════════════════════════════════════════════════════════════════════

function formatCurrency(value) {
  const amount = Number(value || 0);
  return `Rs. ${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatCountLabel(count, singular, plural = `${singular}s`) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : plural}`;
}

// Mandir panchang + operational reports live in modules/workspaces/mandir-operational-reports.js

// Mandir dashboard home + tabs live in modules/workspaces/mandir-dashboard.js
// Mandir dashboard loaders + splash live in modules/workspaces/mandir-dashboard-loaders.js

// Platform dashboard + dashboard preview shell live in modules/workspaces/dashboard-preview-shell.js

// ========== Business Module: Party Master ==========

let activeBusinessWorkspace = "overview";

// Parties list table renderers live in modules/workspaces/business-list-tables.js

// Vouchers list table renderers live in modules/workspaces/business-list-tables.js

// Business workspace dispatcher + router live in modules/workspaces/business-workspace.js

// ══════════════════════════════════════════════════════════════════════

// Financial Health (CFO Insight) — every figure is computed server-side from the
// posted ledger (see app/modules/business/financial_health.py). The frontend only
// renders the trusted KPI/chart/alert payload; it never derives figures itself.

// Render the model's plain-text narrative safely: escape everything, then turn
// blank-line-separated blocks into paragraphs and "-"/"•" lines into list items.
// ══════════════════════════════════════════════════════════════════════
// SECTION: PARTIES — CRUD + dialogs
// API   : GET/POST /api/v1/business/parties  PATCH .../deactivate
// NOTE  : loadBusinessParties, createBusinessParty, updateBusinessParty
// ══════════════════════════════════════════════════════════════════════

// Business list filtering lives in modules/workspaces/business-list-filters.js

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

const businessReportState = {
  tab: "trial-balance",
  as_of: todayIsoDate(),
  from_date: financialYearStartIso(),
  to_date: todayIsoDate(),
  ledgerAccountId: "",
  agingKind: "receivable",
};

// Business reports hub lives in modules/workspaces/business-reports-hub.js

// Export/print toolbars per report tab. Backend supports CSV/XLSX/PDF for the
// core set (trial_balance, party_ledger, itc_reversals, aging, balance_sheet,
// profit_loss); other tabs get Print only for now.
// Print the currently rendered report by cloning its HTML into a clean window —
// avoids fighting the app's global/screen CSS and works across browsers
// (the user picks "Save as PDF" there too if they prefer a browser-rendered PDF).
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

// ========== Business Module: Typed Vouchers ==========

let lastModuleContext = null;

const voucherLineState = [];

// Account helpers + data health live in modules/workspaces/account-helpers.js
// Context helpers (platform owner / business tenant) remain below.

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

async function loadBusinessPartiesForHealth() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/parties?offset=0&limit=20", { method: "GET" });
  setLastBusinessPartiesResult(result);
  if (result.ok) {
    setLastBusinessParties(Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : []);
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

// Account selector helpers live in modules/workspaces/account-selector.js
// Mixed document listeners (allocation + voucher amounts) remain below.

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

// Journal voucher posting lives in modules/workspaces/voucher-create.js
// (createJournalVoucher). An orphaned mid-function remnant was removed here.

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

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

// Mandir create forms + posting dialogs live in modules/workspaces/mandir-create-forms.js

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
  setLastBusinessAccounts([]);
  setLastBusinessParties([]);
  clearVoucherListState();
  setLastAccountingDrilldown(null);
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
  set activeSettingsDetailId(v) { setActiveSettingsDetailId(v); },
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
  set caClientDraft(v) { setCaClientDraft(v); },
  caDocumentAttachmentState,
  get caInviteError() { return caInviteError; },
  set caInviteError(v) { setCaInviteError(v); },
  get caInviteSuccess() { return caInviteSuccess; },
  set caInviteSuccess(v) { setCaInviteSuccess(v); },
  get caPracticeFilters() { return caPracticeFilters; },
  set caPracticeFilters(v) { setCaPracticeFilters(v); },
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
  set coaTypeFilter(v) { setCoaTypeFilter(v); },
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
  set mfgBudgetVsActual(v) { setMfgBudgetVsActual(v); },
  get mfgCompleteFor() { return mfgCompleteFor; },
  set mfgCompleteFor(v) { setMfgCompleteFor(v); },
  mfgCompleteWorkOrder,
  mfgCreateBom,
  mfgCreateBudget,
  mfgCreateCostCentre,
  mfgCreateWorkOrder,
  mfgEnableLayer,
  get mfgError() { return mfgError; },
  set mfgError(v) { setMfgError(v); },
  mfgOpenComplete,
  mfgPl,
  get mfgPlFrom() { return mfgPlFrom; },
  set mfgPlFrom(v) { setMfgPlFrom(v); },
  get mfgPlTo() { return mfgPlTo; },
  set mfgPlTo(v) { setMfgPlTo(v); },
  mfgRemoveBomComponent,
  mfgRemoveWoActual,
  mfgSetBudgetStatus,
  mfgSetWorkOrderStatus,
  get mfgTab() { return mfgTab; },
  set mfgTab(v) { setMfgTab(v); },
  mfgViewBudgetVsActual,
  get mfgWoActualDraft() { return mfgWoActualDraft; },
  set mfgWoActualDraft(v) { setMfgWoActualDraft(v); },
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
  set lastCaDocuments(v) { setLastCaDocuments(v); },
  get lastCaDocumentsResult() { return lastCaDocumentsResult; },
  set lastCaDocumentsResult(v) { setLastCaDocumentsResult(v); },
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
// Wire business reports hub (avoids import cycle with app.js)
// Wire auth + session helpers (avoids import cycle with app.js)
// Wire business workspace dispatcher + router (avoids import cycle with app.js)
// Wire platform dashboard + preview shell (avoids import cycle with app.js)
// Wire navigation shell + module boot renderers (avoids import cycle with app.js)
initNavigationShell({
  appRoot,
  appKeyLabel,
  topbarTitle,
  topbarSubtitle,
  topbarControlStrip,
  brandLogo,
  brandTitle,
  brandSubtitle,
  scopeTitle,
  scopeCopy,
  legacyTitle,
  legacyCopy,
  legacyVideo,
  legacyImage,
  dashboardPreview,
  nav,
  moduleList,
  escapeHtml,
  getExperienceConfig: () => experienceConfig,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getAppKey: () => APP_KEY,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  isProductionShell,
  isMandirHost,
  updateSessionUi,
  updateTrustedContextUi,
  getAccessToken,
  hasTrustedSession,
  activeOrgSelectorType,
  loadBusinessDashboardStats,
  renderDashboardPreview,
  mandirWorkspaceFromModule,
  navIconForMandirWorkspace,
  platformWorkspaceFromModule,
  syncMandirNavActiveState,
  syncGruhaNavActiveState,
  syncPlatformNavActiveState,
  syncBusinessNavActiveState,
  loadModules,
});

initDashboardPreviewShell({
  escapeHtml,
  formatCurrency,
  formatCountMap,
  renderStatCards,
  renderActivity,
  renderPlatformTable,
  renderPendingApprovalsTable,
  getActivePlatformWorkspace: () => activePlatformWorkspace,
  getLastPlatformOwnerDashboard: () => lastPlatformOwnerDashboard,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getLastGruhaData: () => lastGruhaData,
  getLastBusinessDashboardStats: () => lastBusinessDashboardStats,
  activeOrgSelectorType,
  renderGruhaDashboard,
  renderBusinessWorkspace,
  renderSelectedOrgWorkspace,
  renderBusinessExecutiveDashboard,
});

initBusinessWorkspace({
  dashboardPreview,
  nav,
  topbarCurrent,
  escapeHtml,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  setActiveBusinessWorkspace: (value) => { activeBusinessWorkspace = value; },
  getCurrentExperience: () => currentExperience,
  getSelectedOrgType: () => selectedOrgType,
  setSelectedOrgType: (value) => { selectedOrgType = value; },
  getOrgSelectorMeta: () => orgSelectorMeta,
  getExperienceConfig: () => experienceConfig,
  getBusinessReportState: () => businessReportState,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessVouchers: () => lastBusinessVouchers,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastVoucherApprovalQueue: () => lastVoucherApprovalQueue,
  getLastAuditEvents: () => lastAuditEvents,
  getSalesUi: () => salesUi,
  getPurchaseUi: () => purchaseUi,
  getCreditUi: () => creditUi,
  getDebitUi: () => debitUi,
  getHrUi: () => hrUi,
  activeOrgSelectorType,
  updateTrustedContextUi,
  setActiveSettingsDetailId,
  hasTrustedSession,
  updatePageHeader,
  renderMitraBooksSettingsWorkspace,
  renderCaPracticePortalWorkspace,
  renderBusinessPartiesListFilters,
  renderBusinessPartiesTable,
  renderVoucherApprovalQueuePanel,
  renderBusinessVouchersListFilters,
  renderBusinessVouchersTable,
  renderAuditListFilters,
  renderAuditEventsTable,
  renderAccountingDrilldownPanel,
  renderBusinessReportsWorkspace,
  renderBusinessSalesWorkspace,
  renderBusinessPurchaseWorkspace,
  renderBusinessCreditNoteWorkspace,
  renderBusinessDebitNoteWorkspace,
  renderBusinessCoaWorkspace,
  renderFinancialHealthWorkspace,
  renderHrWorkspace,
  renderManufacturingWorkspace,
  renderDashboardPreview,
  loadBusinessDashboardStats,
  loadBusinessParties,
  loadBusinessAccounts,
  loadBusinessVouchers,
  loadVoucherApprovalQueue,
  loadAuditEvents,
  refreshCurrentAccountingDrilldown,
  refreshCurrentBusinessReport,
  loadInvoiceSettings,
  loadBusinessInvoices,
  loadBusinessAdminSettings,
  loadBusinessPartiesForHealth,
  loadAccountingDrilldownResult,
  loadBusinessDataHealth,
  loadBusinessBills,
  loadCreditNotes,
  loadDebitNotes,
  setCoaTypeFilter,
  resetCaPracticeWorkspaceState,
  isBusinessAdmin,
  loadCaAccessUsers,
  loadCaClients,
  loadCaPracticeDocuments,
  loadHrWorkspace,
  setMfgTab,
  setMfgError,
  loadMfgWorkspace,
});

initAuthSession({
  appRoot,
  sessionPill,
  topbarUser,
  topbarAvatar,
  sidebarAvatar,
  sidebarUserName,
  sidebarUserRole,
  loginEmail,
  loginPassword,
  tokenInput,
  accountMenuPanel,
  accountMenuTrigger,
  passwordForm,
  passwordStatus,
  passwordDialog,
  currentPasswordInput,
  newPasswordInput,
  confirmNewPasswordInput,
  currentOrgType,
  currentOrgTenant,
  dashboardPreview,
  apiOutput,
  moduleState,
  getAccessToken,
  getRefreshToken,
  clearAllTokens,
  clearAccessToken,
  setAccessToken,
  setRefreshToken,
  getCurrentExperience: () => currentExperience,
  setCurrentExperience: (value) => { currentExperience = value; },
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getSelectedOrgType: () => selectedOrgType,
  getOrgSelectorMeta: () => orgSelectorMeta,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  getAppKey: () => APP_KEY,
  getLoginEmailStorageKey: () => LOGIN_EMAIL_STORAGE_KEY,
  getDefaultMitraBooksLoginEmail: () => DEFAULT_MITRABOOKS_LOGIN_EMAIL,
  getLoginRequestTimeoutMs: () => LOGIN_REQUEST_TIMEOUT_MS,
  apiRequest,
  renderJson,
  setLoginStatus,
  setAuthPanelMode,
  statusDetailText,
  escapeHtml,
  setLastBusinessAccounts,
  setLastBusinessParties,
  clearVoucherListState,
  setLastAccountingDrilldown,
  renderModules,
  renderModuleState,
  initialExperience,
  mandirPublicPaymentPageUrl,
  loadAndRenderGroupedNav,
  showMandirSplash,
  hideMandirSplash,
  runChecks,
  delay,
});

initBusinessReportsHub({
  escapeHtml,
  todayIsoDate,
  renderJson,
  downloadApiFile,
  getApiOutput: () => apiOutput,
  getBusinessReportState: () => businessReportState,
  getBusinessReportTabs: () => BUSINESS_REPORT_TABS,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getGstReturnState: () => gstReturnState,
  getItcReversalAsOf: () => itcReversalAsOf,
  getTdsQuarter: () => tdsQuarter,
  getBankReconAccountId: () => bankReconAccountId,
  getStatementPartyId: () => statementPartyId,
  getStatementKind: () => statementKind,
  getStatementFromDate: () => statementFromDate,
  getStatementToDate: () => statementToDate,
  getLastBusinessParties: () => lastBusinessParties,
  getLastInventoryItems: () => lastInventoryItems,
  getCreditUi: () => creditUi,
  getDebitUi: () => debitUi,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  loadBusinessParties,
  loadBusinessTrialBalance,
  loadBusinessProfitLoss,
  loadBusinessBalanceSheet,
  loadBusinessReceivablesPayables,
  loadBusinessAging,
  loadUnallocatedPayments,
  loadAllocationReconciliation,
  loadBusinessAllLedgers,
  loadBusinessGeneralLedger,
  loadPeriodLocks,
  loadGstSettlementPreview,
  loadGstr1,
  loadCmp08,
  loadGstr4,
  loadGstr3b,
  loadItcReversalPreview,
  loadTdsRegister,
  loadBankReconciliation,
  loadBankCashBook,
  loadPartyStatement,
  loadFixedAssets,
  loadDimensions,
  loadDimensionReport,
  loadBranchConsolidatedReport,
  loadInventoryItems,
  loadInventoryPolicy,
  loadStockMovements,
  loadStockRegister,
  loadClosingStockEntries,
  reportDateControls,
  renderBusinessTrialBalance,
  renderBusinessProfitLoss,
  renderBusinessBalanceSheet,
  renderBusinessGeneralLedger,
  renderBusinessReceivablesPayables,
  renderBusinessAging,
  renderPaymentAllocation,
  renderPeriodLocksPanel,
  renderGstSettlementPanel,
  renderGstReturns,
  renderItcReversalPanel,
  renderTdsRegisterPanel,
  renderBankReconPanel,
  renderBankCashBookPanel,
  renderStatementsPanel,
  renderOpeningYearEndPanel,
  renderFixedAssetsPanel,
  renderDimensionsPanel,
  renderInventoryPanel,
});

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

// Wire voucher creation helpers (avoids import cycle with app.js / vouchers.js)
// Wire parties CRUD (avoids import cycle with app.js)
// Wire Chart of Accounts workspace (avoids import cycle with app.js)
// Wire CA practice loaders (avoids import cycle with app.js)
// Wire Financial Health (avoids import cycle with app.js)
// Wire Accounting Drilldown (avoids import cycle with app.js)
// Wire voucher form helpers (avoids import cycle with app.js)
// Wire account/dashboard loaders (avoids import cycle with app.js)
// Wire account selector helpers (avoids import cycle with app.js)
// Wire account helpers + data health + books health (avoids import cycle with app.js)
// Wire executive dashboard (avoids import cycle with app.js)
// Wire parties/vouchers list table renderers (avoids import cycle with app.js)
// Wire business attachments (avoids import cycle with app.js)
// Wire MitraBooks settings workspace (avoids import cycle with app.js)
// Wire business list filtering (avoids import cycle with app.js)
// Wire dashboard stat/activity primitives (avoids import cycle with app.js)
// Wire Mandir panchang + operational reports (avoids import cycle with app.js)
// Wire Mandir dashboard home + tabs (avoids import cycle with app.js)
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

// Wire Mandir dashboard loaders + splash (avoids import cycle with app.js)
initMandirDashboardLoaders({
  mandirSplash,
  mandirSplashVideo,
  mandirSplashImage,
  brandSplashCopy,
  dashboardPreview,
  apiOutput,
  apiRequest,
  renderJson,
  buildQueryString,
  todayIsoDate,
  mandirListPath,
  mandirPublicPaymentsPath,
  mandirPublicPaymentExceptionsPath,
  loadAccountingDrilldownResult,
  getCurrentExperience: () => currentExperience,
  getLastMandirPaymentAccounts: () => lastMandirPaymentAccounts,
  setLastMandirPaymentAccounts: (value) => { lastMandirPaymentAccounts = value; },
  getLastMandirAccounts: () => lastMandirAccounts,
  setLastMandirAccounts: (value) => { lastMandirAccounts = value; },
  getLastMandirPanchang: () => lastMandirPanchang,
  setLastMandirPanchang: (value) => { lastMandirPanchang = value; },
  getLastMandirModuleConfig: () => lastMandirModuleConfig,
  setLastMandirModuleConfig: (value) => { lastMandirModuleConfig = value; },
  getLastMandirComplianceConfig: () => lastMandirComplianceConfig,
  setLastMandirComplianceConfig: (value) => { lastMandirComplianceConfig = value; },
  getLastMandirOperationalReports: () => lastMandirOperationalReports,
  setLastMandirOperationalReports: (value) => { lastMandirOperationalReports = value; },
  getLastMandirReceipt: () => lastMandirReceipt,
  getLastMandirFormResult: () => lastMandirFormResult,
});

initMandirDashboard({
  escapeHtml,
  formatCurrency,
  formatCountLabel,
  renderStatCards,
  renderActivity,
  isProductionShell,
  isMandirHost,
  renderMandirWorkspaceTabs,
  renderMandirOperationResult,
  renderMandirCreateForms,
  renderMandirListFilters,
  renderMandirDonationsTable,
  renderMandirSevaBookingsTable,
  mandirPublicPaymentPageUrl,
  renderMandirPublicPaymentFilters,
  renderMandirPublicPaymentsTable,
  renderMandirExceptionFilters,
  renderMandirExceptionsTable,
  renderMandirReceiptHistoryTable,
  renderMandirPanchang,
  renderMandirOperationalReports,
  renderMandirDevoteesView,
  renderAccountingDrilldownPanel,
  renderMandirTrialBalance,
  renderMandirFinancialReports,
  renderMandirExpensesTable,
  getActiveMandirWorkspace: () => activeMandirWorkspace,
  getMandirReportState: () => mandirReportState,
  getLastMandirPanchang: () => lastMandirPanchang,
  getLastMandirOperationalReports: () => lastMandirOperationalReports,
});

initMandirOperationalReports({
  escapeHtml,
  formatCurrency,
  renderStatCards,
  getLastMandirPanchang: () => lastMandirPanchang,
  getLastMandirOperationalReports: () => lastMandirOperationalReports,
});

initDashboardPrimitives({
  escapeHtml,
  formatCurrency,
});

initBusinessListFilters({
  loadBusinessParties,
  loadBusinessVouchers,
});

initSettingsWorkspace({
  escapeHtml,
  setLoginStatus,
  statusDetailText,
  renderBusinessDataHealthPanel,
  plannedOrgWorkspaceModel,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});

initAttachments({
  escapeHtml,
  getAccessToken,
  buildFrontendApiUrl,
});

initBusinessListTables({
  escapeHtml,
  formatCurrency,
  getBusinessListState: () => businessListState,
});

initExecutiveDashboard({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  renderStatCards,
  hasTrustedSession,
  getLastAccountingDrilldown: () => lastAccountingDrilldown,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastBusinessDashboardStats: () => lastBusinessDashboardStats,
  getLastBusinessMisKpis: () => lastBusinessMisKpis,
  getBusinessDashboardLoadInFlight: () => businessDashboardLoadInFlight,
  getBusinessMisLoadInFlight: () => businessMisLoadInFlight,
  loadBusinessDashboardStats,
  loadBusinessMisKpis,
});

initAccountHelpers({
  escapeHtml,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastBusinessAccountsResult: () => lastBusinessAccountsResult,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessPartiesResult: () => lastBusinessPartiesResult,
  getLastModuleContext: () => lastModuleContext,
  getLastAccountingDrilldown: () => lastAccountingDrilldown,
  getLastBusinessDataHealth: () => lastBusinessDataHealth,
  getBusinessDataHealthLoadInFlight: () => businessDataHealthLoadInFlight,
  loadBusinessDataHealth,
  hasTrustedSession,
  enabledModuleKeys,
  isBusinessTenantContext,
});

initAccountSelector({
  escapeHtml,
  businessAccountsForSelection,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  filterBusinessAccountsByQuery,
  populateAccountPickerSelect,
  normalizeBusinessAccount,
  updateVoucherBalance,
});

initAccountLoading({
  setLoginStatus,
  statusDetailText,
  accountRowsFromPayload,
  loadModuleContextForAccounts,
  isBusinessModuleEnabled,
  refreshVoucherAccountSelects,
  updateVoucherAccountsStatus,
  hasTrustedSession,
  getCurrentExperience: () => currentExperience,
  getDashboardPreview: () => dashboardPreview,
  getExperienceConfig: () => experienceConfig,
  renderDashboardPreview: (config) => renderDashboardPreview(config),
  getApiOutput: () => apiOutput,
  getDefaultMitraBooksLoginEmail: () => DEFAULT_MITRABOOKS_LOGIN_EMAIL,
  businessAccountsForSelection,
});

initVoucherForm({
  escapeHtml,
  formatCurrency,
  normalizeBusinessAccount,
  businessAccountLabel,
  renderAccountSelectorComponent,
  refreshVoucherAccountDatalist,
  updateVoucherAccountsStatus,
  populateVoucherAccountSelect,
  getLastBusinessAccounts: () => lastBusinessAccounts,
});

initAccountingDrilldown({
  escapeHtml,
  formatCurrency,
  buildQueryString,
  getActiveAppKey: () => EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY,
  getApiOutput: () => apiOutput,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  getExperienceConfig: () => experienceConfig,
  renderDashboardPreview: (config) => renderDashboardPreview(config),
  loadMandirDashboard: () => loadMandirDashboard(),
});

initFinancialHealth({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  getApiOutput: () => apiOutput,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});

initCaPractice({
  setLoginStatus,
  statusDetailText,
  getApiOutput: () => apiOutput,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  listBusinessAttachments,
  escapeHtml,
  renderBusinessAttachmentPanel,
  uploadBusinessAttachmentFiles,
  isCaViewer,
  isBusinessAdmin,
  plannedOrgWorkspaceModel,
});

initCoa({
  escapeHtml,
  statusDetailText,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  loadBusinessAccounts,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});

initParties({
  setLoginStatus,
  statusDetailText,
  getBusinessListState: () => businessListState,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
});

initVoucherCreate({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  findBusinessAccountById,
  accountIdForVoucherPayload,
  voucherDimensionPayload,
  clearVoucherForm,
  loadBusinessVouchers,
  loadVoucherApprovalQueue,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
});

// Wire vouchers CRUD/list (avoids import cycle with app.js)
initVouchers({
  escapeHtml,
  setLoginStatus,
  statusDetailText,
  getBusinessListState: () => businessListState,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastDimensions: () => lastDimensions,
  loadBusinessAccounts,
  loadBusinessParties,
  loadDimensions,
  renderAccountSelectorComponent,
  dimensionOptions,
  addVoucherLine,
  updateVoucherBalance,
  clearVoucherForm,
  loadVoucherPartyOutstanding,
  createBusinessVoucherByType,
  getBusinessVoucherCreateForm: () => document.getElementById("business-voucher-create-form"),
  getBusinessVoucherCreateDialog: () => document.getElementById("business-voucher-create-dialog"),
});

// HEADER & HEALTH WIDGET (Phase 1C Step 7)
// ============================================

// Books health widget lives in modules/workspaces/account-helpers.js

function updatePageHeader(parentName = "Workspaces", currentName = "Dashboard", pageTitle = "Dashboard Workspace") {
  const breadcrumbParent = document.getElementById("breadcrumb-parent");
  const breadcrumbCurrent = document.getElementById("breadcrumb-current");
  const viewTitle = document.getElementById("view-title");

  if (breadcrumbParent) breadcrumbParent.textContent = parentName;
  if (breadcrumbCurrent) breadcrumbCurrent.textContent = currentName;
  if (viewTitle) viewTitle.textContent = pageTitle;
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

