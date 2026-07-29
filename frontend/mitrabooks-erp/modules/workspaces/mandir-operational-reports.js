// ====================================================================
// SECTION: MANDIR — PANCHANG + OPERATIONAL REPORTS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirOperationalReports(...).
// ====================================================================

import { accountingDrilldownState } from "./accounting-drilldown.js";
import { formatCountLabel } from "./shared-render-utils.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initMandirOperationalReports(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirOperationalReports() must be called before using Mandir operational report helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }

export function panchangTimeRange(value) {
  if (!value || typeof value !== "object") {
    return "--";
  }
  const start = value.start || value.start_time || "";
  const end = value.end || value.end_time || "";
  return start && end ? `${start} - ${end}` : start || end || "--";
}

export function renderMandirPanchang(payload = getLastMandirPanchang()) {
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

export function reportPayload(value, fallback = {}) {
  if (!value) {
    return fallback;
  }
  if (value.ok === false) {
    return fallback;
  }
  return value;
}

export function reportRows(value, key) {
  const payload = reportPayload(value);
  return Array.isArray(payload[key]) ? payload[key] : [];
}

export function renderMandirOperationalReports(reports = getLastMandirOperationalReports()) {
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

export function renderMandirDevoteesView(reports = getLastMandirOperationalReports()) {
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

