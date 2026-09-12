// ADR-014 Path A: live MitraBooks MIS pull UI (imported by office-ai-mis-dashboard.js).

export const MIS_LIVE_STATE_DEFAULTS = {
  misLiveEnabled: false,
  misLiveStatus: null,
  misLastLiveReport: null,
};

export function applyMisLivePing(state, payload) {
  state.misLiveEnabled = !!payload?.mis_capabilities?.live_mitrabooks;
}

export function clearMisLivePing(state) {
  state.misLiveEnabled = false;
  state.misLiveStatus = null;
}

export function renderMisLivePullSection(state, { canEdit, escapeHtml }) {
  if (!state?.misLiveEnabled) {
    return `<p class="muted" style="margin-top:1rem;">Live MitraBooks pull requires <code>office_ai.mis.live_mitrabooks</code>.</p>`;
  }
  const report = state.misLastLiveReport;
  const reportHtml = report
    ? `<div class="muted" style="margin-top:0.5rem;">
        Last live pull: ${escapeHtml(String(report.facts_upserted ?? 0))} fact(s) upserted,
        ${escapeHtml(String(report.facts_replaced ?? 0))} prior MitraBooks fact(s) replaced,
        ${escapeHtml(String((report.warnings || []).length))} warning(s).
        ${Array.isArray(report.warnings) && report.warnings.length
          ? ` (${escapeHtml(report.warnings.join(", "))})`
          : ""}
      </div>`
    : "";
  const status = state.misLiveStatus;
  const statusHtml = status
    ? `<p class="muted" style="margin-top:0.35rem;">Probe: ${escapeHtml(status.enabled ? "ready" : (status.reason || "unavailable"))}${status.has_pnl_rows === false ? " · books empty for current month" : ""}.</p>`
    : "";
  return `
    <div class="stack-form" style="margin-top:1rem;" data-office-ai-mis-live>
      <h5>Pull from MitraBooks</h5>
      <p class="muted">Reads P&amp;L, balance sheet, cash, and AR/AP ageing for the pack period via report services. Replaces only <code>source_system=mitrabooks</code> facts (Excel/manual kept). Never posts journals.</p>
      <button class="secondary" type="button" data-office-ai-action="mis-live-status">Check status</button>
      <button class="primary" type="button" data-office-ai-action="mis-pull-mitrabooks" ${canEdit ? "" : "disabled"}>Pull from MitraBooks</button>
      ${statusHtml}
      ${reportHtml}
    </div>`;
}

export async function handleMisLiveAction(action, el, { state, apiRequest, unwrap, refreshMisFacts, refreshMisData }) {
  if (action === "mis-live-status") {
    const payload = unwrap(await apiRequest("/api/v1/officemitra/mis/live-mitrabooks/status"));
    state.misLiveStatus = payload || null;
    state.notice = payload?.enabled
      ? (payload.has_pnl_rows ? "MitraBooks live reads are available." : "Live reads available; current-month books look empty.")
      : `Live reads unavailable: ${payload?.reason || "unknown"}.`;
    return true;
  }
  if (action === "mis-pull-mitrabooks") {
    const packId = String(state.misSelectedPackId || "").trim();
    if (!packId) throw new Error("Select a pack first");
    const result = unwrap(await apiRequest(
      `/api/v1/officemitra/mis/packs/${encodeURIComponent(packId)}/import/mitrabooks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accounting_entity_id: "primary" }),
      },
    ));
    state.misLastLiveReport = {
      facts_upserted: result?.facts_upserted,
      facts_replaced: result?.facts_replaced,
      warnings: result?.warnings || [],
    };
    const warnings = Array.isArray(result?.warnings) ? result.warnings : [];
    state.notice = warnings.includes("empty_books_no_facts")
      ? "Live pull finished with no MitraBooks facts (empty books). Import Excel or post demo vouchers first — numbers were not invented."
      : `Live pull: ${Number(result?.facts_upserted || 0)} MitraBooks fact(s) upserted.`;
    if (typeof refreshMisFacts === "function") await refreshMisFacts(packId);
    if (typeof refreshMisData === "function") await refreshMisData();
    return true;
  }
  return false;
}
