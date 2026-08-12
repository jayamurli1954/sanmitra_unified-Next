
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
import { initOfficeAiWorkspace, renderOfficeAiWorkspace, loadOfficeAiWorkspace } from "./modules/workspaces/office-ai.js";
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
import { initShellUi, updatePageHeader, initializeHeader } from "./modules/shell-ui.js";

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
  isPasswordRecoveryPanelOpen,
  setAuthPanelMode,
  showAuthFieldMessage,
  clearAuthFieldMessage,
  requestPasswordReset,
  completePasswordReset,
  setLoginStatus,
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
  mandirWorkspaceFromModule,
  platformWorkspaceFromModule,
  navIconForMandirWorkspace,
  syncMandirNavActiveState,
  syncGruhaNavActiveState,
  syncPlatformNavActiveState,
} from "./modules/workspaces/navigation-shell.js";

import {
  initOrgWorkspace,
  plannedOrgWorkspaceModel,
  renderSelectedOrgWorkspace,
} from "./modules/workspaces/org-workspace.js";

import {
  initShellBoot,
  runChecks,
  loadPlatformOwnerDashboard,
  setExperience,
} from "./modules/workspaces/shell-boot.js";

import {
  initPlatformOwnerOps,
  approveOnboardingRequest,
  rejectOnboardingRequest,
  openTenantEntitlementsDialog,
  submitTenantEntitlements,
  setPlatformWorkspace,
} from "./modules/workspaces/platform-owner-ops.js";

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
  buildFrontendApiUrl,
  resultPayload,
  resultRows,
  statusDetailText,
  renderStatusBlock,
  currentBillingPeriodQuery,
  renderSimpleTable,
  escapeHtml,
  formatCountMap,
  renderPlatformTable,
  renderPendingApprovalsTable,
  mandirPublicPaymentPageUrl,
  renderMandirOperationResult,
  delay,
  formatCurrency,
  formatCountLabel,
} from "./modules/workspaces/shared-render-utils.js";

import {
  initBusinessEntryHelpers,
  hasTdsSectionsCache,
  loadTdsSections,
  tdsSectionRate,
  tdsSectionOptions,
  isBusinessAdmin,
  isCaViewer,
  round2,
  reversalDateBounds,
  reversalPanel,
  focusBusinessEntryField,
} from "./modules/workspaces/business-entry-helpers.js";

import {
  initContextPathHelpers,
  isBusinessModuleEnabled,
  enabledModuleKeys,
  isPlatformOwnerContext,
  isBusinessTenantContext,
  loadBusinessPartiesForHealth,
  loadModuleContextForAccounts,
  buildQueryString,
  mandirListPath,
  mandirPublicPaymentsPath,
  mandirPublicPaymentExceptionsPath,
  todayIsoDate,
} from "./modules/workspaces/context-path-helpers.js";

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
// Org / planned-suite workspace renderers live in modules/workspaces/org-workspace.js

// Business executive dashboard lives in modules/workspaces/executive-dashboard.js
// Shared render/format utils live in modules/workspaces/shared-render-utils.js

// Nav workspace mapping + sync live in modules/workspaces/navigation-shell.js
// Auth + session helpers (incl. setLoginStatus) live in modules/workspaces/auth-session.js

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
// Reversal must stay within the document's GST month. Returns the date input
// bounds + a sensible default (today if in-month, else month end).
// Business entry helpers live in modules/workspaces/business-entry-helpers.js
// ========== Business Module: Typed Vouchers ==========

let lastModuleContext = null;

const voucherLineState = [];

// Account helpers + data health live in modules/workspaces/account-helpers.js
// Context + Mandir list path helpers live in modules/workspaces/context-path-helpers.js

// Account selector helpers live in modules/workspaces/account-selector.js
// Mixed document listeners (allocation + voucher amounts) remain below.

// Account selector helpers + document listeners live in modules/workspaces/account-selector.js

// Journal voucher posting lives in modules/workspaces/voucher-create.js
// (createJournalVoucher). An orphaned mid-function remnant was removed here.
// Shell boot (runChecks / setExperience / platform dashboard) lives in modules/workspaces/shell-boot.js

// Context + Mandir list path helpers live in modules/workspaces/context-path-helpers.js
// Mandir create forms + posting dialogs live in modules/workspaces/mandir-create-forms.js
// Platform-owner onboarding/entitlements live in modules/workspaces/platform-owner-ops.js
// Mandir verification/cancel dialogs live in modules/workspaces/mandir-create-forms.js

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
initOfficeAiWorkspace({ escapeHtml, apiRequest, downloadApiFile, dashboardPreview, appKey: "mitrabooks", getActiveBusinessWorkspace: () => activeBusinessWorkspace });
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
  hasTdsSectionsCache,
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
  hasTdsSectionsCache,
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
  initializeHealthWidget,
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
// Wire org / planned-suite workspace renderers (avoids import cycle with app.js)
// Wire shell boot helpers (avoids import cycle with app.js)
// Wire platform-owner onboarding/entitlements ops (avoids import cycle with app.js)
initPlatformOwnerOps({
  apiOutput,
  dashboardPreview,
  entitlementDialog,
  entitlementTenantId,
  entitlementTenantLabel,
  entitlementPlan,
  entitlementStatus,
  entitlementModules,
  apiRequest,
  renderJson,
  escapeHtml,
  loadPlatformOwnerDashboard,
  syncPlatformNavActiveState,
  renderPlatformDashboard,
  emptyPlatformDashboardPayload,
  getAppKey: () => APP_KEY,
  getEntitlementModulesByOrgType: () => entitlementModulesByOrgType,
  getLastPlatformOwnerDashboard: () => lastPlatformOwnerDashboard,
  setCurrentExperience: (value) => { currentExperience = value; },
  setActivePlatformWorkspace: (value) => { activePlatformWorkspace = value; },
});

initShellBoot({
  healthPill,
  apiOutput,
  moduleState,
  dashboardPreview,
  getAccessToken,
  clearAllTokens,
  loadHealth,
  loadModules,
  statusLabel,
  moduleItemsFromPayload,
  renderJson,
  renderModuleState,
  updateTrustedContextUi,
  updateSessionUi,
  renderModules,
  setLoginStatus,
  isPasswordRecoveryPanelOpen,
  isPlatformOwnerContext,
  apiRequest,
  renderPlatformDashboard,
  syncPlatformNavActiveState,
  loadMandirDashboard,
  loadGruhaDashboard,
  loadBusinessAccounts,
  loadBusinessPartiesForHealth,
  loadAccountingDrilldownResult,
  refreshBooksHealthWidget,
  renderDashboardPreview,
  emptyPlatformDashboardPayload,
  loadAndRenderGroupedNav,
  getCurrentExperience: () => currentExperience,
  setCurrentExperience: (value) => { currentExperience = value; },
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getLastPlatformOwnerDashboard: () => lastPlatformOwnerDashboard,
  setLastPlatformOwnerDashboard: (value) => { lastPlatformOwnerDashboard = value; },
  getActivePlatformWorkspace: () => activePlatformWorkspace,
  setActivePlatformWorkspace: (value) => { activePlatformWorkspace = value; },
  getExperienceConfig: () => experienceConfig,
  getExperienceAppKeys: () => EXPERIENCE_APP_KEYS,
  getAppKey: () => APP_KEY,
});

initOrgWorkspace({
  escapeHtml,
  activeOrgSelectorType,
  renderCaPracticePortalWorkspace,
  renderProfessionalSuiteWorkspace,
  renderCaDocumentIntake,
});

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
  topbarCurrent,
  escapeHtml,
  getExperienceConfig: () => experienceConfig,
  getCurrentExperience: () => currentExperience,
  getActiveMandirWorkspace: () => activeMandirWorkspace,
  getActiveGruhaWorkspace: () => activeGruhaWorkspace,
  getActivePlatformWorkspace: () => activePlatformWorkspace,
  updatePageHeader,
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
  loadHrWorkspace, loadOfficeAiWorkspace, renderOfficeAiWorkspace,
  setMfgTab, setMfgError, loadMfgWorkspace,
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
  forgotPasswordForm,
  forgotPasswordEmail,
  resetPasswordForm,
  resetNewPasswordInput,
  resetConfirmPasswordInput,
  loginStatus,
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
  getPendingPasswordResetToken: () => pendingPasswordResetToken,
  setPendingPasswordResetToken: (value) => { pendingPasswordResetToken = value; },
  apiRequest,
  renderJson,
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

// Apply auth panel mode only after initAuthSession so form refs are bound.
if (pendingPasswordResetToken) {
  setAuthPanelMode("reset");
  setLoginStatus("warn", "Reset link opened", "Enter a new password to complete the reset.");
} else {
  setAuthPanelMode("login");
}

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
  getLastVoucherApprovalQueue: () => lastVoucherApprovalQueue,
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

// Wire business entry helpers (avoids import cycle with app.js)
// Wire context + Mandir list path helpers (avoids import cycle with app.js)
initContextPathHelpers({
  apiRequest,
  loadModules,
  setLastBusinessPartiesResult,
  setLastBusinessParties,
  getLastModuleContext: () => lastModuleContext,
  setLastModuleContext: (value) => { lastModuleContext = value; },
  getMandirListState: () => mandirListState,
  getMandirListPageSize: () => MANDIR_LIST_PAGE_SIZE,
});

initBusinessEntryHelpers({
  apiRequest,
  escapeHtml,
  todayIsoDate,
  getLastModuleContext: () => lastModuleContext,
});

initAccountSelector({
  escapeHtml,
  businessAccountsForSelection,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  filterBusinessAccountsByQuery,
  populateAccountPickerSelect,
  normalizeBusinessAccount,
  updateVoucherBalance,
  setAllocationLineAmount,
  loadVoucherPartyOutstanding,
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

// Header helpers live in modules/shell-ui.js; books health widget in account-helpers.js
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

window.setBusinessWorkspace = (ws) => setBusinessWorkspace(ws);
renderModuleState(moduleState);
document.documentElement.dataset.mitrabooksShellHandlersReady = "1";
void (async () => {
  try {
    await runChecks();
  } finally {
    document.documentElement.dataset.mitrabooksShellReady = "1";
  }
})();

