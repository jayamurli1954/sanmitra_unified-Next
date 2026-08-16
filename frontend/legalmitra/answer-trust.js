/** Compact Stage 2.1 trust affordances for the LegalMitra answer card. */

export function formatCitationAuditLine(payload, escapeHtml) {
  const audit = payload?.citation_audit;
  if (!audit || typeof audit !== "object") {
    return "";
  }
  const verified = Number(audit.verified_count || 0);
  const mismatch = Number(audit.mismatch_count || 0);
  const unverifiable = Number(audit.unverifiable_count || 0);
  const claims = Number(audit.claim_count || 0);
  if (!claims && verified === 0 && mismatch === 0 && unverifiable === 0) {
    return "";
  }
  const gate = payload?.quality_gate;
  const gateBit = gate && typeof gate === "object"
    ? ` · gate ${gate.passed ? "pass" : "fail"}`
    : "";
  return `<div class="legal-answer-audit" role="status">Sources checked: ${escapeHtml(String(verified))} verified · ${escapeHtml(String(mismatch))} mismatch · ${escapeHtml(String(unverifiable))} unverifiable${escapeHtml(gateBit)}</div>`;
}
