// ====================================================================
// SECTION: ACCOUNTING DRILLDOWN (shared MandirMitra + MitraBooks)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountingDrilldown(...).
// API: GET /api/v1/accounting/reports/drilldown and voucher detail.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

const todayForReports = new Date();
const firstDayForReports = new Date(todayForReports.getFullYear(), todayForReports.getMonth(), 1);

export let accountingDrilldownState = {
  level: "month",
  from_date: firstDayForReports.toISOString().slice(0, 10),
  to_date: todayForReports.toISOString().slice(0, 10),
  month: "",
  week_start: "",
  day: "",
};
export let lastAccountingDrilldown = null;
export let lastAccountingVoucherDetail = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountingDrilldown(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountingDrilldown() must be called before using accounting drilldown helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function buildQueryString(params) { return requireDeps().buildQueryString(params); }
function getActiveAppKey() { return requireDeps().getActiveAppKey(); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function renderDashboardPreview(config) { return requireDeps().renderDashboardPreview(config); }
function loadMandirDashboard() { return requireDeps().loadMandirDashboard(); }

export function setLastAccountingDrilldown(value) {
  lastAccountingDrilldown = value;
}

export function setLastAccountingVoucherDetail(value) {
  lastAccountingVoucherDetail = value;
}

export function setAccountingDrilldownState(value) {
  accountingDrilldownState = value;
}

export function accountingDrilldownTitle(level) {
  return {
    month: "Monthly Voucher Drill Down",
    week: "Weekly Voucher Drill Down",
    day: "Daily Voucher Drill Down",
    voucher: "Voucher Level",
  }[level] || "Accounting Drill Down";
}

export function renderAccountingDrilldownRows(payload) {
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

export function renderAccountingVoucherDetail(detail = lastAccountingVoucherDetail) {
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

export function renderAccountingDrilldownPanel(payload = lastAccountingDrilldown) {
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

export function accountingDrilldownPath() {
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

export async function loadAccountingDrilldownResult() {
  const activeAppKey = getActiveAppKey();
  const result = await apiRequest(activeAppKey, accountingDrilldownPath(), { method: "GET" });
  lastAccountingDrilldown = result.ok ? result.payload : result;
  return result;
}


export async function loadAccountingVoucherDetail(journalId) {
  if (!journalId) {
    return null;
  }
  const activeAppKey = getActiveAppKey();
  const result = await apiRequest(activeAppKey, `/api/v1/accounting/reports/vouchers/${encodeURIComponent(journalId)}`, { method: "GET" });
  lastAccountingVoucherDetail = result.ok ? result.payload : result;
  return result;
}

export function readAccountingDrilldownFilterValues() {
  const panel = getDashboardPreview().querySelector("[data-accounting-drilldown]");
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

export async function refreshCurrentAccountingDrilldown() {
  const result = await loadAccountingDrilldownResult();
  renderJson(getApiOutput(), { accounting_drilldown: result });
  if (getCurrentExperience() === "mandir") {
    await loadMandirDashboard();
  } else if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "accounting") {
    getDashboardPreview().innerHTML = renderAccountingDrilldownPanel();
  } else {
    getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig()[getCurrentExperience()]);
  }
}

export async function applyAccountingDrilldownFilters() {
  const values = readAccountingDrilldownFilterValues();
  if (!values) {
    return;
  }
  accountingDrilldownState = values;
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

export async function resetAccountingDrilldown() {
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

export async function drillAccountingReport(button) {
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

export async function openAccountingVoucherDetail(button) {
  const journalId = button.getAttribute("data-journal-id") || "";
  const result = await loadAccountingVoucherDetail(journalId);
  renderJson(getApiOutput(), { accounting_voucher_detail: result });
  if (getCurrentExperience() === "mandir") {
    await loadMandirDashboard();
  } else {
    getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig()[getCurrentExperience()]);
  }
}

