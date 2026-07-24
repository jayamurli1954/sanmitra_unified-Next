// ====================================================================
// SECTION: STAT CARDS + ACTIVITY + RECENT VOUCHERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDashboardPrimitives(...).
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initDashboardPrimitives(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDashboardPrimitives() must be called before using dashboard primitives");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }

export function renderStatCards(stats) {
  return stats.map(([label, value, subtext]) => `
    <article class="metric-tile">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${subtext}</small>
    </article>
  `).join("");
}

export function renderActionTiles(actions) {
  return actions.map((action) => `
    <button class="quick-tile" type="button">
      <span class="quick-icon">${action.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span>
      <span>${action}</span>
    </button>
  `).join("");
}

export function renderActivity(items) {
  return items.map((item) => `<li><span class="activity-dot"></span><span>${item}</span></li>`).join("");
}

export function renderBusinessRecentVoucherRows(rows) {
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

