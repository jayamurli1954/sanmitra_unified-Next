// ====================================================================
// SECTION: BANK RECONCILIATION (+ bank/cash book)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBankRecon(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBankRecon = null;
export let bankReconAccountId = "";
export let lastBankCashBook = null;
export let bankCashBookType = "all";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initBankRecon(injected) {
  deps = injected;
}

/** Used by app.js report filters (imported let binding is read-only). */
export function setBankCashBookType(value) {
  bankCashBookType = String(value || "all");
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBankRecon() must be called before using bank-recon helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// SECTION: BANK RECONCILIATION
// API   : POST /api/v1/business/bank-recon/statement  GET /api/v1/business/bank-recon
// NOTE  : loadBankReconciliation, uploadBankStatementFile, confirmBankReconMatch
// ══════════════════════════════════════════════════════════════════════

export function bankAccountOptions() {
  // Cash/bank accounts live in the 11xxx subclass of the business COA.
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("11"));
}

export async function loadBankCashBook() {
  const params = new URLSearchParams();
  params.set("from_date", getBusinessReportState().from_date);
  params.set("to_date", getBusinessReportState().to_date);
  params.set("book_type", bankCashBookType);
  const result = await apiRequest("mitrabooks", `/api/v1/business/banking/books?${params.toString()}`, { method: "GET" });
  lastBankCashBook = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { bank_cash_book: { ok: result.ok, status: result.status, book_type: bankCashBookType } });
}

export async function loadBankReconciliation(accountId) {
  bankReconAccountId = String(accountId || bankReconAccountId || "");
  if (!bankReconAccountId) { rerenderBusinessReportsIfActive(); return; }
  const result = await apiRequest("mitrabooks", `/api/v1/business/bank-recon?account_id=${encodeURIComponent(bankReconAccountId)}`, { method: "GET" });
  lastBankRecon = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { bank_recon: { ok: result.ok, account_id: bankReconAccountId } });
}

export async function uploadBankStatementFile() {
  const accountSel = document.querySelector("[data-bankrecon-account]");
  const fileInput = document.querySelector("[data-bankrecon-file]");
  const accountId = accountSel?.value || bankReconAccountId;
  if (!accountId) {
    setLoginStatus("warn", "Pick a bank account", "Choose which ledger bank account this statement belongs to.");
    return;
  }
  const file = fileInput?.files?.[0];
  if (!file) {
    setLoginStatus("warn", "Choose a file", "Upload the bank statement CSV exported from net banking.");
    return;
  }
  const csvText = await file.text();
  bankReconAccountId = accountId;
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/business/bank-recon/statement?account_id=${encodeURIComponent(accountId)}`,
    { method: "POST", body: JSON.stringify({ csv: csvText }) },
  );
  if (result.ok) {
    const r = result.payload || {};
    setLoginStatus("ok", "Statement imported", `${r.inserted || 0} line(s) added, ${r.skipped_duplicates || 0} duplicate(s) skipped.`);
    await loadBankReconciliation(accountId);
  } else {
    setLoginStatus("danger", "Import failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_statement_upload: { ok: result.ok, status: result.status } });
}

export async function confirmBankReconMatch(statementLineId, lineId) {
  const result = await apiRequest("mitrabooks", "/api/v1/business/bank-recon/match", {
    method: "POST",
    body: JSON.stringify({
      account_id: Number(bankReconAccountId),
      statement_line_id: statementLineId,
      line_id: Number(lineId),
    }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Matched", "Statement line matched to the book entry.");
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Match failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_recon_match: { ok: result.ok, status: result.status } });
}

export async function confirmBankReconGroupMatch(statementLineIds, lineIds) {
  const stmtIds = (statementLineIds || []).map((id) => String(id || "").trim()).filter(Boolean);
  const bookIds = (lineIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0);
  const result = await apiRequest("mitrabooks", "/api/v1/business/bank-recon/match-group", {
    method: "POST",
    body: JSON.stringify({
      account_id: Number(bankReconAccountId),
      statement_line_ids: stmtIds,
      line_ids: bookIds,
    }),
  });
  if (result.ok) {
    const r = result.payload || {};
    setLoginStatus("ok", "Group matched", `${stmtIds.length} bank line(s) matched to ${bookIds.length} book entr${bookIds.length === 1 ? "y" : "ies"} for ${formatCurrency(Number(r.amount || 0))}.`);
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Group match failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_recon_group_match: { ok: result.ok, status: result.status } });
}

/** Manual matching: whatever the user ticked in the two unmatched tables. */
export async function matchSelectedBankReconLines() {
  const stmtIds = [...document.querySelectorAll("[data-bankrecon-pick-stmt]:checked")].map((el) => el.getAttribute("data-bankrecon-pick-stmt") || "");
  const bookIds = [...document.querySelectorAll("[data-bankrecon-pick-book]:checked")].map((el) => el.getAttribute("data-bankrecon-pick-book") || "");
  if (!stmtIds.length || !bookIds.length) {
    setLoginStatus("warn", "Select lines to match", "Tick at least one bank line and one book entry. One side must have a single line.");
    return;
  }
  if (stmtIds.length === 1 && bookIds.length === 1) {
    await confirmBankReconMatch(stmtIds[0], bookIds[0]);
    return;
  }
  await confirmBankReconGroupMatch(stmtIds, bookIds);
}

/**
 * Match lines whose totals differ (bank charges, MDR, TDS, rounding) and post
 * the difference to the chosen offset account through the voucher path.
 * `offsetKey` names the offset <select> to read ("manual" for the ticked lines).
 */
export async function confirmBankReconDifferenceMatch(statementLineIds, lineIds, offsetKey) {
  const stmtIds = (statementLineIds || []).map((id) => String(id || "").trim()).filter(Boolean);
  const bookIds = (lineIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0);
  const offsetAccountId = document.querySelector(`[data-bankrecon-diff-offset="${CSS.escape(String(offsetKey || ""))}"]`)?.value || "";
  if (!stmtIds.length || !bookIds.length) {
    setLoginStatus("warn", "Select lines to match", "Tick at least one bank line and one book entry. One side must have a single line.");
    return;
  }
  if (!offsetAccountId) {
    setLoginStatus("warn", "Pick an account for the difference", "For example Bank Charges, TDS Receivable or Round-off.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/bank-recon/match-difference", {
    method: "POST",
    body: JSON.stringify({
      account_id: Number(bankReconAccountId),
      statement_line_ids: stmtIds,
      line_ids: bookIds,
      offset_account_id: Number(offsetAccountId),
      approve: true,
    }),
  });
  if (result.ok) {
    const r = result.payload || {};
    if (r.status === "active") {
      setLoginStatus("ok", "Matched with difference", `Difference of ${formatCurrency(Number(r.difference || 0))} posted and the lines are reconciled.`);
    } else {
      setLoginStatus("warn", "Waiting for approval", r.note || "The difference voucher is waiting for approval.");
    }
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Match with difference failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_recon_difference_match: { ok: result.ok, status: result.status } });
}

export async function matchSelectedBankReconLinesWithDifference() {
  const stmtIds = [...document.querySelectorAll("[data-bankrecon-pick-stmt]:checked")].map((el) => el.getAttribute("data-bankrecon-pick-stmt") || "");
  const bookIds = [...document.querySelectorAll("[data-bankrecon-pick-book]:checked")].map((el) => el.getAttribute("data-bankrecon-pick-book") || "");
  await confirmBankReconDifferenceMatch(stmtIds, bookIds, "manual");
}

export async function completeBankReconDifferenceMatch(matchGroupId) {
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/business/bank-recon/match-difference/${encodeURIComponent(matchGroupId)}/complete`,
    { method: "POST" },
  );
  if (result.ok) {
    setLoginStatus("ok", "Match completed", "The approved difference voucher was added and the lines are reconciled.");
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Could not complete the match", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_recon_difference_complete: { ok: result.ok, status: result.status } });
}

export async function reverseBankReconMatch(matchId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/bank-recon/match/${encodeURIComponent(matchId)}/reverse`, { method: "POST" });
  if (result.ok) {
    const grouped = Number(result.payload?.reversed_rows || 0) > 1;
    const voucherNote = result.payload?.note ? ` ${result.payload.note}` : "";
    setLoginStatus("ok", "Unmatched", (grouped
      ? `The whole group (${result.payload.reversed_rows} pairs) was reversed; all its lines are open again.`
      : "The match was reversed; both lines are open again.") + voucherNote);
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Unmatch failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_recon_unmatch: { ok: result.ok, status: result.status } });
}

export function renderBankCashBookPanel() {
  const payload = lastBankCashBook;
  if (!payload) return `<p class="muted">Loading bank and cash book...</p>`;
  if (payload.ok === false) return reportUnavailablePanel("Bank / Cash Book", payload);
  const s = payload.summary || {};
  const num = (value) => escapeHtml(formatCurrency(Number(value || 0)));
  const accountSections = (payload.accounts || []).map((account) => {
    const rows = (account.lines || []).map((line) => `
      <tr>
        <td>${escapeHtml(line.entry_date || "")}</td>
        <td>${escapeHtml(line.reference || "")}</td>
        <td>${escapeHtml(line.description || "")}</td>
        <td>${escapeHtml(line.source_document_type || "")}</td>
        <td class="amount">${Number(line.receipt || 0) > 0 ? num(line.receipt) : ""}</td>
        <td class="amount">${Number(line.payment || 0) > 0 ? num(line.payment) : ""}</td>
        <td class="amount">${num(line.running_balance)}</td>
      </tr>`).join("");
    return `
      <div class="table-preview compact-table">
        <h4>${escapeHtml(`${account.account_code || ""} - ${account.account_name || ""}`)} <span class="pill">${escapeHtml(account.book_type || "")}</span></h4>
        <div class="metric-grid three">
          ${renderStatCards([
            ["Opening", formatCurrency(account.opening_balance || 0), "before period"],
            ["Receipts", formatCurrency(account.total_receipts || 0), "period debit"],
            ["Payments", formatCurrency(account.total_payments || 0), "period credit"],
          ])}
        </div>
        <table>
          <thead><tr><th>Date</th><th>Reference</th><th>Description</th><th>Source</th><th class="amount">Receipt</th><th class="amount">Payment</th><th class="amount">Balance</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="7" class="muted">No cash/bank movement in this period.</td></tr>`}</tbody>
          <tfoot><tr><th colspan="6">Closing balance</th><th class="amount">${num(account.closing_balance)}</th></tr></tfoot>
        </table>
      </div>`;
  }).join("");
  return `
    <div class="preview-heading compact">
      <div>
        <h4>Bank / Cash Book</h4>
        <p>${escapeHtml(payload.from_date || getBusinessReportState().from_date)} to ${escapeHtml(payload.to_date || getBusinessReportState().to_date)} · ${escapeHtml(String(s.account_count || 0))} cash/bank account(s)</p>
      </div>
      <span class="pill">${escapeHtml(payload.book_type || bankCashBookType)}</span>
    </div>
    <div class="metric-grid four">
      ${renderStatCards([
        ["Opening", formatCurrency(s.opening_balance || 0), "before period"],
        ["Receipts", formatCurrency(s.total_receipts || 0), "cash/bank debits"],
        ["Payments", formatCurrency(s.total_payments || 0), "cash/bank credits"],
        ["Closing", formatCurrency(s.closing_balance || 0), "opening + receipts - payments"],
      ])}
    </div>
    ${accountSections || `<p class="muted">No cash or bank accounts found for this tenant and book type.</p>`}
  `;
}

export async function postBankReconStatementVoucher(statementLineId) {
  const offsetAccountId = document.querySelector(`[data-bankrecon-offset="${CSS.escape(statementLineId)}"]`)?.value || "";
  if (!bankReconAccountId || !statementLineId) {
    setLoginStatus("warn", "Pick a bank line", "Load bank reconciliation and choose a bank-only statement line.");
    return;
  }
  if (!offsetAccountId) {
    setLoginStatus("warn", "Pick an offset account", "Choose the expense, income, or clearing account for this bank-only line.");
    return;
  }
  const line = (lastBankRecon?.in_bank_not_in_books || []).find((item) => item.statement_line_id === statementLineId) || {};
  const result = await apiRequest("mitrabooks", "/api/v1/business/bank-recon/statement-voucher", {
    method: "POST",
    headers: { "X-Idempotency-Key": `bank-statement-voucher:${statementLineId}:${offsetAccountId}` },
    body: JSON.stringify({
      account_id: Number(bankReconAccountId),
      statement_line_id: statementLineId,
      offset_account_id: Number(offsetAccountId),
      description: line.description || "Bank statement adjustment",
      reference: line.ref || undefined,
      approve: true,
    }),
  });
  if (result.ok) {
    const voucher = result.payload?.voucher || {};
    const label = voucher.voucher_number || voucher.voucher_id || "Voucher";
    if (result.payload?.posting_status === "posted") {
      setLoginStatus("ok", "Voucher posted", result.payload?.match
        ? `${label} posted and the bank line is now reconciled.`
        : `${label} posted from the bank statement line.`);
    } else {
      setLoginStatus("warn", "Waiting for approval", result.payload?.note || `${label} was created and is waiting for approval.`);
    }
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Voucher posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bank_statement_voucher: { ok: result.ok, status: result.status, statement_line_id: statementLineId } });
}

export function renderBankReconPanel() {
  const accounts = bankAccountOptions();
  const offsetOptions = businessAccountsForSelection()
    .filter((account) => String(account.id) !== String(bankReconAccountId))
    .map((account) => `<option value="${escapeHtml(String(account.id))}">${escapeHtml(`${account.code} - ${account.name}`)}</option>`)
    .join("");
  const options = `<option value="">Select bank account</option>` + accounts.map((a) =>
    `<option value="${escapeHtml(String(a.id))}" ${String(a.id) === String(bankReconAccountId) ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Bank account <select data-bankrecon-account>${options}</select></label>
      <button class="secondary" type="button" data-business-action="bankrecon-load">Load</button>
      <label>Statement CSV <input type="file" accept=".csv,text/csv" data-bankrecon-file></label>
      <button class="secondary" type="button" data-business-action="bankrecon-upload">Import statement</button>
    </div>
    <p class="muted">Export the account statement as CSV from net banking and import it here. Lines are matched against the posted ledger; confirming a match never changes the books.</p>`;
  if (!bankReconAccountId) return `${controls}<p class="muted">Select a bank account to begin.</p>`;
  const r = lastBankRecon;
  if (!r) return `${controls}<p class="muted">Loading bank reconciliation...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Bank Reconciliation", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.summary || {};
  const diff = s.difference;
  const clean = diff !== null && diff !== undefined && Number(diff) === 0;

  const cards = [
    ["Balance as per books", s.book_balance, `${s.book_lines_total || 0} ledger line(s)`],
    ["Balance as per bank", s.statement_balance, `${s.statement_lines_total || 0} statement line(s)`],
    ["Expected bank balance", s.expected_statement_balance, "books + reconciling items"],
    ["Difference", diff, clean ? "fully reconciled" : "investigate unmatched lines"],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${val === null || val === undefined ? "—" : num(val)}</strong></div></div>
    </article>`).join("");

  const suggestionRows = (r.suggestions || []).map((g) => `
    <tr>
      <td>${escapeHtml(g.statement?.txn_date || "")}</td>
      <td>${escapeHtml(g.statement?.description || g.statement?.ref || "")}</td>
      <td>${escapeHtml(g.book?.entry_date || "")}</td>
      <td>${escapeHtml(g.book?.reference || g.book?.description || "")}</td>
      <td class="amount">${num(g.amount)}</td>
      <td><span class="pill ${g.confidence === "ref" ? "ok" : ""}">${escapeHtml(g.confidence === "ref" ? "reference" : `±${g.date_diff_days}d`)}</span></td>
      <td><button class="primary" type="button" data-business-action="bankrecon-match" data-stmt-id="${escapeHtml(g.statement_line_id || "")}" data-line-id="${escapeHtml(String(g.line_id || ""))}">Match</button></td>
    </tr>`).join("");

  const groupLabel = (g) => (g.group_type === "many_to_one" ? "several bank → 1 book" : "1 bank → several book");
  const stackLines = (items, dateKey, textKeys) => items.map((item) =>
    `<div>${escapeHtml(item[dateKey] || "")} · ${escapeHtml(textKeys.map((k) => item[k]).find(Boolean) || "")} · ${num(item.amount)}</div>`).join("");
  const groupSuggestionRows = (r.group_suggestions || []).map((g) => `
    <tr>
      <td><span class="pill">${escapeHtml(groupLabel(g))}</span></td>
      <td>${stackLines(g.statement || [], "txn_date", ["description", "ref"])}</td>
      <td>${stackLines(g.book || [], "entry_date", ["reference", "description"])}</td>
      <td class="amount">${num(g.amount)}</td>
      <td><span class="pill ${g.confidence === "ambiguous" ? "warn" : "ok"}">${escapeHtml(g.confidence === "ambiguous" ? "check: other combinations fit" : `exact sum ±${g.max_date_diff_days}d`)}</span></td>
      <td><button class="primary" type="button" data-business-action="bankrecon-match-group" data-stmt-ids="${escapeHtml((g.statement_line_ids || []).join(","))}" data-line-ids="${escapeHtml((g.line_ids || []).join(","))}">Match group</button></td>
    </tr>`).join("");

  const offsetSelect = (key) => `
    <select data-bankrecon-diff-offset="${escapeHtml(key)}">
      <option value="">Account for difference</option>
      ${offsetOptions}
    </select>`;
  const differenceRows = (r.difference_suggestions || []).map((g, i) => `
    <tr>
      <td>${escapeHtml(g.statement?.txn_date || "")} · ${escapeHtml(g.statement?.description || g.statement?.ref || "")}</td>
      <td>${escapeHtml(g.book?.entry_date || "")} · ${escapeHtml(g.book?.reference || g.book?.description || "")}</td>
      <td class="amount">${num(g.statement_amount)}</td>
      <td class="amount">${num(g.book_amount)}</td>
      <td class="amount"><strong>${num(g.difference)}</strong></td>
      <td><span class="pill warn">${escapeHtml(g.hint_text || "")}</span></td>
      <td>${offsetSelect(`sugg-${i}`)}</td>
      <td><button class="primary" type="button" data-business-action="bankrecon-match-difference" data-stmt-ids="${escapeHtml(String(g.statement_line_id || ""))}" data-line-ids="${escapeHtml(String(g.line_id || ""))}" data-offset-key="${escapeHtml(`sugg-${i}`)}">Match &amp; post difference</button></td>
    </tr>`).join("");

  const pendingRows = (r.pending_differences || []).map((p) => `
    <tr>
      <td>${escapeHtml(String((p.statement_line_ids || []).length))} bank / ${escapeHtml(String((p.line_ids || []).length))} book line(s)</td>
      <td class="amount">${num(p.statement_total)}</td>
      <td class="amount">${num(p.book_total)}</td>
      <td class="amount">${num(p.difference)}</td>
      <td>${escapeHtml(p.adjustment_voucher_id || "")}</td>
      <td>
        <button class="primary" type="button" data-business-action="bankrecon-complete-difference" data-group-id="${escapeHtml(p.match_group_id || "")}">Complete match</button>
        <button class="secondary" type="button" data-business-action="bankrecon-unmatch" data-match-id="${escapeHtml(p.match_id || "")}">Unmatch</button>
      </td>
    </tr>`).join("");

  const bankOnlyRows = (r.in_bank_not_in_books || []).map((l) => `
    <tr>
      <td><input type="checkbox" aria-label="Select bank line" data-bankrecon-pick-stmt="${escapeHtml(l.statement_line_id || "")}"></td>
      <td>${escapeHtml(l.txn_date || "")}</td>
      <td>${escapeHtml(l.description || "")}</td>
      <td>${escapeHtml(l.ref || "")}</td>
      <td class="amount">${Number(l.deposit || 0) > 0 ? num(l.deposit) : ""}</td>
      <td class="amount">${Number(l.withdrawal || 0) > 0 ? num(l.withdrawal) : ""}</td>
      <td>
        <select data-bankrecon-offset="${escapeHtml(l.statement_line_id || "")}">
          <option value="">Offset account</option>
          ${offsetOptions}
        </select>
      </td>
      <td><button class="secondary" type="button" data-business-action="bankrecon-post-voucher" data-stmt-id="${escapeHtml(l.statement_line_id || "")}">Post voucher</button></td>
    </tr>`).join("");

  const bookOnlyRows = (r.in_books_not_in_bank || []).map((l) => `
    <tr>
      <td><input type="checkbox" aria-label="Select book entry" data-bankrecon-pick-book="${escapeHtml(String(l.line_id || ""))}"></td>
      <td>${escapeHtml(l.entry_date || "")}</td>
      <td>${escapeHtml(l.reference || "")}</td>
      <td>${escapeHtml(l.description || "")}</td>
      <td class="amount">${Number(l.debit || 0) > 0 ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) > 0 ? num(l.credit) : ""}</td>
    </tr>`).join("");

  const matchedRows = (r.matched || []).map((m) => `
    <tr>
      <td>${escapeHtml(m.statement_txn_date || "")}</td>
      <td>${escapeHtml(m.book_entry_date || "")}</td>
      <td>${escapeHtml(m.side || "")}${m.match_group_id ? ` <span class="pill">group · ${escapeHtml(String(m.group_size || ""))} lines</span>` : ""}${m.is_adjustment ? ` <span class="pill warn">difference voucher</span>` : ""}</td>
      <td class="amount">${num(m.amount)}</td>
      <td><button class="secondary" type="button" data-business-action="bankrecon-unmatch" data-match-id="${escapeHtml(m.match_id || "")}">Unmatch</button></td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(`${r.account?.code || ""} - ${r.account?.name || ""}`)} as of ${escapeHtml(r.as_of || "")} · ${escapeHtml(String(s.matched_count || 0))} matched.</p></div>
      <span class="pill ${clean ? "ok" : "warn"}">${clean ? "reconciled" : (diff === null || diff === undefined ? "no statement balance" : "difference " + formatCurrency(Number(diff)))}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>

    <div class="table-preview compact-table">
      <h4>Suggested matches (confirm each — nothing is applied automatically)</h4>
      <table>
        <thead><tr><th>Bank date</th><th>Bank narration</th><th>Book date</th><th>Book entry</th><th class="amount">Amount</th><th>Basis</th><th></th></tr></thead>
        <tbody>${suggestionRows || `<tr><td colspan="7" class="muted">No suggestions — nothing left that agrees on amount within the date window.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Suggested group matches: one line equals the sum of several on the other side</h4>
      <table>
        <thead><tr><th>Type</th><th>Bank line(s)</th><th>Book entr(ies)</th><th class="amount">Amount</th><th>Basis</th><th></th></tr></thead>
        <tbody>${groupSuggestionRows || `<tr><td colspan="6" class="muted">No group suggestions. Nothing left sums exactly within the date window.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Near-matches: amounts differ slightly (bank charges, MDR, TDS, rounding)</h4>
      <table>
        <thead><tr><th>Bank line</th><th>Book entry</th><th class="amount">Bank</th><th class="amount">Books</th><th class="amount">Difference</th><th>Likely reason</th><th>Post difference to</th><th></th></tr></thead>
        <tbody>${differenceRows || `<tr><td colspan="8" class="muted">No near-matches. Nothing left differs from a book entry by only a small amount.</td></tr>`}</tbody>
      </table>
      <p class="muted">The difference is posted as a journal voucher on this bank account. The lines count as matched only once that voucher is posted.</p>
    </div>

    ${pendingRows ? `
    <div class="table-preview compact-table">
      <h4>Waiting for the difference voucher to be approved (${escapeHtml(String((r.pending_differences || []).length))})</h4>
      <table>
        <thead><tr><th>Lines</th><th class="amount">Bank</th><th class="amount">Books</th><th class="amount">Difference</th><th>Voucher</th><th></th></tr></thead>
        <tbody>${pendingRows}</tbody>
      </table>
    </div>` : ""}

    <div class="report-date-controls">
      <button class="secondary" type="button" data-business-action="bankrecon-match-selected">Match selected</button>
      <span class="muted">Tick bank lines and book entries below to match them by hand. One side must have a single line, and the totals must agree exactly.</span>
    </div>
    <div class="report-date-controls">
      ${offsetSelect("manual")}
      <button class="secondary" type="button" data-business-action="bankrecon-match-selected-difference">Match selected &amp; post difference</button>
      <span class="muted">Use this when the ticked totals differ, for example TDS deducted by the customer.</span>
    </div>

    <div class="table-preview compact-table">
      <h4>In bank, not in books (${escapeHtml(String((r.in_bank_not_in_books || []).length))}) — post these (charges, interest, direct credits)</h4>
      <table>
        <thead><tr><th></th><th>Date</th><th>Narration</th><th>Ref</th><th class="amount">Deposit</th><th class="amount">Withdrawal</th><th>Offset</th><th></th></tr></thead>
        <tbody>${bankOnlyRows || `<tr><td colspan="8" class="muted">Every bank line is matched or suggested.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In books, not in bank (${escapeHtml(String((r.in_books_not_in_bank || []).length))}) — uncleared cheques / deposits in transit</h4>
      <table>
        <thead><tr><th></th><th>Date</th><th>Reference</th><th>Description</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>${bookOnlyRows || `<tr><td colspan="6" class="muted">Every book line is reflected in the bank statement.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Matched (${escapeHtml(String((r.matched || []).length))})</h4>
      <table>
        <thead><tr><th>Bank date</th><th>Book date</th><th>Side</th><th class="amount">Amount</th><th></th></tr></thead>
        <tbody>${matchedRows || `<tr><td colspan="5" class="muted">No confirmed matches yet.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- TDS / TCS quarterly register (Form 26Q / 27EQ working paper) -------- //

// ══════════════════════════════════════════════════════════════════════
