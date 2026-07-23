// ====================================================================
// SECTION: CUSTOMER STATEMENTS + DUNNING
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initStatements(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastPartyStatement = null;
export let statementPartyId = "";
export let statementKind = "receivable";
export let statementFromDate = "";
export let statementToDate = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initStatements(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initStatements() must be called before using statement helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// ══════════════════════════════════════════════════════════════════════
// SECTION: CUSTOMER STATEMENTS + DUNNING
// API   : GET /api/v1/business/statements/{party_id}  POST .../dunning
// NOTE  : loadPartyStatement, recordDunningSent, renderStatementsPanel
// ══════════════════════════════════════════════════════════════════════

export async function loadPartyStatement() {
  const partySel = document.querySelector("[data-stmt-party]");
  const kindSel = document.querySelector("[data-stmt-kind]");
  const fromInput = document.querySelector("[data-stmt-from]");
  const toInput = document.querySelector("[data-stmt-to]");
  if (partySel) statementPartyId = partySel.value || statementPartyId;
  if (kindSel) statementKind = kindSel.value || statementKind;
  if (fromInput) statementFromDate = fromInput.value || "";
  if (toInput) statementToDate = toInput.value || "";
  if (!statementPartyId) { rerenderBusinessReportsIfActive(); return; }
  const params = new URLSearchParams({ kind: statementKind });
  if (statementFromDate) params.set("from_date", statementFromDate);
  if (statementToDate) params.set("to_date", statementToDate);
  const result = await apiRequest("mitrabooks", `/api/v1/business/statements/${encodeURIComponent(statementPartyId)}?${params.toString()}`, { method: "GET" });
  lastPartyStatement = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { party_statement: { ok: result.ok, party_id: statementPartyId, kind: statementKind } });
}

export async function recordDunningSent() {
  const s = lastPartyStatement;
  const suggestion = s?.dunning?.suggestion;
  if (!suggestion || !suggestion.level) {
    setLoginStatus("warn", "Nothing to record", "No overdue invoices — no reminder is suggested.");
    return;
  }
  const note = document.querySelector("[data-dunning-note]")?.value || "";
  const result = await apiRequest("mitrabooks", `/api/v1/business/statements/${encodeURIComponent(statementPartyId)}/dunning`, {
    method: "POST",
    body: JSON.stringify({ level: suggestion.level, note, overdue_total: suggestion.overdue_total }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Reminder recorded", `${suggestion.label} logged for this party.`);
    await loadPartyStatement();
  } else {
    setLoginStatus("danger", "Could not record", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { dunning_record: { ok: result.ok, status: result.status } });
}

export function copyDunningLetter() {
  const letter = lastPartyStatement?.dunning?.letter || "";
  if (!letter) { setLoginStatus("warn", "No letter", "Load a party with overdue invoices first."); return; }
  navigator.clipboard?.writeText(letter).then(
    () => setLoginStatus("ok", "Letter copied", "Paste it into your email/WhatsApp and send."),
    () => setLoginStatus("warn", "Copy failed", "Select the letter text and copy manually."),
  );
}

export function renderStatementsPanel() {
  const parties = Array.isArray(getLastBusinessParties()) ? getLastBusinessParties() : [];
  const options = `<option value="">Select party</option>` + parties.map((p) =>
    `<option value="${escapeHtml(p.party_id)}" ${p.party_id === statementPartyId ? "selected" : ""}>${escapeHtml(p.party_name)} (${escapeHtml(p.party_type || "")})</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Party <select data-stmt-party>${options}</select></label>
      <label>Side <select data-stmt-kind>
        <option value="receivable" ${statementKind === "receivable" ? "selected" : ""}>Receivable (customer)</option>
        <option value="payable" ${statementKind === "payable" ? "selected" : ""}>Payable (vendor)</option>
      </select></label>
      <label>From <input type="date" data-stmt-from value="${escapeHtml(statementFromDate)}"></label>
      <label>To <input type="date" data-stmt-to value="${escapeHtml(statementToDate)}"></label>
      <button class="secondary" type="button" data-business-action="stmt-load">Load</button>
    </div>
    <p class="muted">Dates default to the current financial year. The statement is built from the posted party sub-ledger.</p>`;
  if (!statementPartyId) return `${controls}<p class="muted">Select a customer or vendor to generate their statement of account.</p>`;
  const r = lastPartyStatement;
  if (!r) return `${controls}<p class="muted">Loading statement...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Statement of Account", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));

  const txnRows = (r.transactions || []).map((t) => `
    <tr>
      <td>${escapeHtml(t.entry_date || "")}</td>
      <td>${escapeHtml(t.document_type || "")}</td>
      <td>${escapeHtml(t.reference || "")}</td>
      <td>${escapeHtml(t.description || "")}</td>
      <td class="amount">${Number(t.debit || 0) ? num(t.debit) : ""}</td>
      <td class="amount">${Number(t.credit || 0) ? num(t.credit) : ""}</td>
      <td class="amount">${num(t.balance)}</td>
    </tr>`).join("");

  const openRows = (r.open_items || []).map((i) => `
    <tr>
      <td>${escapeHtml(i.open_item_number || "")}</td>
      <td>${escapeHtml(i.item_date || "")}</td>
      <td>${escapeHtml(i.due_date || "—")}</td>
      <td class="amount">${num(i.total)}</td>
      <td class="amount">${num(i.outstanding)}</td>
      <td class="amount">${escapeHtml(String(i.days_overdue ?? 0))}</td>
    </tr>`).join("");

  const d = r.dunning || {};
  const sug = d.suggestion || {};
  const dunningMessage = sug.level
    ? `Suggested: <strong>${escapeHtml(sug.label || "")}</strong> — oldest invoice ${escapeHtml(String(sug.max_days_overdue || 0))} days overdue, ${escapeHtml(String(sug.overdue_count || 0))} invoice(s), total ${num(sug.overdue_total)}.`
    : (sug.label === "Allocation required" ? "Allocation required — the ledger is settled or differs from open-item allocation, so no reminder is generated." : "Nothing overdue — no reminder needed.");
  const logRows = (d.log || []).map((l) => `
    <tr>
      <td>${escapeHtml(String(l.created_at || "").slice(0, 10))}</td>
      <td>${escapeHtml(l.label || `Level ${l.level}`)}</td>
      <td class="amount">${l.overdue_total ? num(l.overdue_total) : ""}</td>
      <td>${escapeHtml(l.note || "")}</td>
      <td>${escapeHtml(l.created_by || "")}</td>
    </tr>`).join("");

  const dunningPanel = r.kind !== "receivable" ? "" : `
    <div class="table-preview compact-table">
      <h4>Payment reminders (dunning)</h4>
      <div class="preview-heading compact">
        <div><p>${dunningMessage}</p></div>
        <span class="pill ${sug.level >= 3 ? "warn" : sug.level ? "" : "ok"}">${escapeHtml(sug.level ? `Level ${sug.level}` : "clear")}</span>
      </div>
      ${d.letter ? `
      <pre style="white-space:pre-wrap;border:1px solid var(--line,#ddd);border-radius:6px;padding:10px;font-size:12px;max-height:280px;overflow:auto;">${escapeHtml(d.letter)}</pre>
      <div class="report-date-controls">
        <button class="secondary" type="button" data-business-action="dunning-copy">Copy letter</button>
        <label>Note <input type="text" data-dunning-note placeholder="e.g. emailed to accounts@..." maxlength="200"></label>
        <button class="primary" type="button" data-business-action="dunning-record">Record reminder sent</button>
      </div>` : ""}
      <h4 style="margin-top:12px;">Reminder history</h4>
      <table>
        <thead><tr><th>Date</th><th>Level</th><th class="amount">Overdue then</th><th>Note</th><th>By</th></tr></thead>
        <tbody>${logRows || `<tr><td colspan="5" class="muted">No reminders recorded yet.</td></tr>`}</tbody>
      </table>
    </div>`;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>Statement for <strong>${escapeHtml(r.party?.party_name || "")}</strong> (${escapeHtml(r.kind)}) · ${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)} · from ${escapeHtml(r.business_name || "")}.</p></div>
      <span class="pill">Closing ${num(r.closing_balance)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>Statement of account</h4>
      <table>
        <thead><tr><th>Date</th><th>Document</th><th>Reference</th><th>Particulars</th><th class="amount">Debit</th><th class="amount">Credit</th><th class="amount">Balance</th></tr></thead>
        <tbody>
          <tr><td>${escapeHtml(r.from_date)}</td><td></td><td></td><td><em>Opening balance</em></td><td class="amount"></td><td class="amount"></td><td class="amount">${num(r.opening_balance)}</td></tr>
          ${txnRows || `<tr><td colspan="7" class="muted">No transactions in this period.</td></tr>`}
        </tbody>
        <tfoot><tr><th colspan="4">Closing balance</th><td class="amount">${num(r.total_debit)}</td><td class="amount">${num(r.total_credit)}</td><td class="amount"><strong>${num(r.closing_balance)}</strong></td></tr></tfoot>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Open items (${escapeHtml(String((r.open_items || []).length))})</h4>
      <table>
        <thead><tr><th>Document</th><th>Date</th><th>Due</th><th class="amount">Total</th><th class="amount">Outstanding</th><th class="amount">Days overdue</th></tr></thead>
        <tbody>${openRows || `<tr><td colspan="6" class="muted">Nothing outstanding — the account is settled.</td></tr>`}</tbody>
      </table>
    </div>
    ${dunningPanel}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}
