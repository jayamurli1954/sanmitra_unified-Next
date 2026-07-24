// ====================================================================
// SECTION: MANDIR — DASHBOARD LOADERS + SPLASH + TB LEDGER
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirDashboardLoaders(...).
// ====================================================================

import { accountingDrilldownState } from "./accounting-drilldown.js";
import { mandirReportState } from "./mandir-financial-reports.js";
import { mandirReceiptRowsFromLists } from "./mandir-tables.js";
import { renderMandirDashboard } from "./mandir-dashboard.js";

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let mandirSplash;
let mandirSplashVideo;
let mandirSplashImage;
let brandSplashCopy;
let dashboardPreview;
let apiOutput;

export function initMandirDashboardLoaders(injected) {
  deps = injected;
  mandirSplash = injected.mandirSplash;
  mandirSplashVideo = injected.mandirSplashVideo;
  mandirSplashImage = injected.mandirSplashImage;
  brandSplashCopy = injected.brandSplashCopy;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirDashboardLoaders() must be called before using Mandir dashboard loaders");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function buildQueryString(...args) { return requireDeps().buildQueryString(...args); }
function todayIsoDate(...args) { return requireDeps().todayIsoDate(...args); }
function mandirListPath(...args) { return requireDeps().mandirListPath(...args); }
function mandirPublicPaymentsPath(...args) { return requireDeps().mandirPublicPaymentsPath(...args); }
function mandirPublicPaymentExceptionsPath(...args) { return requireDeps().mandirPublicPaymentExceptionsPath(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getLastMandirPaymentAccounts() { return requireDeps().getLastMandirPaymentAccounts(); }
function setLastMandirPaymentAccounts(value) { requireDeps().setLastMandirPaymentAccounts(value); }
function getLastMandirAccounts() { return requireDeps().getLastMandirAccounts(); }
function setLastMandirAccounts(value) { requireDeps().setLastMandirAccounts(value); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function setLastMandirPanchang(value) { requireDeps().setLastMandirPanchang(value); }
function getLastMandirModuleConfig() { return requireDeps().getLastMandirModuleConfig(); }
function setLastMandirModuleConfig(value) { requireDeps().setLastMandirModuleConfig(value); }
function getLastMandirComplianceConfig() { return requireDeps().getLastMandirComplianceConfig(); }
function setLastMandirComplianceConfig(value) { requireDeps().setLastMandirComplianceConfig(value); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }
function setLastMandirOperationalReports(value) { requireDeps().setLastMandirOperationalReports(value); }
function getLastMandirReceipt() { return requireDeps().getLastMandirReceipt(); }
function getLastMandirFormResult() { return requireDeps().getLastMandirFormResult(); }

export async function showMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  const splashConfig = getCurrentExperience() === "mandir"
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

export function hideMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  mandirSplash.classList.remove("show");
  mandirSplash.setAttribute("aria-hidden", "true");
  mandirSplashVideo?.pause();
}

export async function loadMandirDashboard() {
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
    setLastMandirPaymentAccounts(paymentAccounts.payload || { cash_accounts: [], bank_accounts: [] });
  }
  if (accounts.ok && Array.isArray(accounts.payload)) {
    setLastMandirAccounts(accounts.payload);
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
  setLastMandirPanchang(panchang.ok ? panchang.payload : panchang);
  setLastMandirModuleConfig(moduleConfig.ok ? moduleConfig.payload : getLastMandirModuleConfig());
  setLastMandirComplianceConfig(complianceConfig.ok ? complianceConfig.payload : getLastMandirComplianceConfig());
  setLastMandirOperationalReports({
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
    inventory_enabled: Boolean((moduleConfig.ok ? moduleConfig.payload : getLastMandirModuleConfig())?.module_inventory_enabled),
  });
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
    panchang: getLastMandirPanchang(),
    operational_reports: getLastMandirOperationalReports(),
    module_config: getLastMandirModuleConfig(),
    compliance_config: getLastMandirComplianceConfig(),
    payment_accounts: paymentAccounts.ok ? paymentAccounts.payload : getLastMandirPaymentAccounts(),
    accounts: accounts.ok && Array.isArray(accounts.payload) ? accounts.payload : getLastMandirAccounts(),
    receipt: getLastMandirReceipt(),
    form_result: getLastMandirFormResult(),
    live_data_available: hasLiveData,
  });
}

export async function openMandirTrialBalanceLedger(button) {
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

