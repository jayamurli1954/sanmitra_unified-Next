/**
 * Court Fee Calculator — intake + config-driven rule engine.
 * Rules live in ./data/court-fee-rules.json so state schedules can be updated
 * without changing calculator code. Amounts are orientation only.
 */

let _rulesCache = null;

export async function loadCourtFeeRules() {
  if (_rulesCache) return _rulesCache;
  const response = await fetch(new URL("./data/court-fee-rules.json", import.meta.url));
  if (!response.ok) {
    throw new Error("Could not load court-fee rules configuration");
  }
  _rulesCache = await response.json();
  return _rulesCache;
}

function escape(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function courtFeeToolBodyHtml(rules) {
  const states = Object.entries(rules.states || {})
    .map(([key, state]) => `<option value="${escape(key)}">${escape(state.label)}</option>`)
    .join("");
  const caseTypes = (rules.case_types || [])
    .map((row) => `<option value="${escape(row.key)}">${escape(row.label)}</option>`)
    .join("");
  const commonCaveats = (rules.common_caveats || [])
    .map((item) => `<li>${escape(item)}</li>`)
    .join("");

  return `
    <p class="legal-tool-intake-lead">
      Court fee is governed by <strong>state-specific</strong> Court Fees / Suits Valuation legislation.
      LegalMitra needs <strong>State</strong>, <strong>Case type</strong>, and <strong>Suit value</strong> before calculating or opening AI.
      Fee tables are loaded from a maintainable rules config — not hard-coded in the calculator UI.
    </p>
    <div class="legal-tool-intake-grid">
      <label>Step 1 — State / UT
        <select id="tool-court-state">
          <option value="">Select state…</option>
          ${states}
        </select>
      </label>
      <label>Step 2 — Case type
        <select id="tool-court-case-type">
          <option value="">Select case type…</option>
          ${caseTypes}
        </select>
      </label>
      <label>Step 3 — Suit value (₹)
        <input id="tool-court-suit-value" type="number" min="0" placeholder="Example: 1500000">
      </label>
      <label>Additional reliefs / notes (optional)
        <input id="tool-court-notes" maxlength="240" placeholder="e.g. injunction + damages; appeal from decree">
      </label>
    </div>
    <button type="button" data-tool-action="court-fee">Calculate court fee orientation</button>
    <div class="legal-tool-result" id="tool-result">
      Complete Steps 1–3, then calculate. Output includes applicable Act, section/schedule hints, formula notes, orientation amount (where safe), and state caveats.
    </div>
    <div class="legal-tool-checklist">
      <h4>Common caveats</h4>
      <ul class="legal-tool-caveat-list">${commonCaveats}</ul>
      <p class="legal-tool-config-meta">Rules config version: ${escape(rules.version || "unknown")}</p>
    </div>
  `;
}

export function readCourtFeeIntake() {
  return {
    stateKey: String(document.getElementById("tool-court-state")?.value || "").trim(),
    caseType: String(document.getElementById("tool-court-case-type")?.value || "").trim(),
    suitValue: Number(document.getElementById("tool-court-suit-value")?.value || 0),
    notes: String(document.getElementById("tool-court-notes")?.value || "").trim(),
  };
}

export function missingCourtFeeFields(intake = readCourtFeeIntake()) {
  const missing = [];
  if (!intake.stateKey) missing.push("State / UT");
  if (!intake.caseType) missing.push("Case type");
  if (!intake.suitValue || intake.suitValue <= 0) missing.push("Suit value");
  return missing;
}

function caseTypeLabel(rules, key) {
  return (rules.case_types || []).find((row) => row.key === key)?.label || key;
}

function resolveRule(rules, intake) {
  const state = rules.states?.[intake.stateKey];
  if (!state) return { error: "Selected state is not in the court-fee rules config." };
  const rule = state.case_rules?.[intake.caseType];
  if (!rule) {
    return {
      error: `No rule configured for case type “${intake.caseType}” in ${state.label}. Update court-fee-rules.json.`,
    };
  }
  return { state, rule };
}

function computeOrientationFee(rule, suitValue) {
  if (rule.fee_mode !== "ad_valorem_orientation") {
    return {
      amount: null,
      detail: "Schedule verification required — no ad-valorem orientation percentage is configured for this case type.",
    };
  }
  const pct = Number(rule.orientation_pct || 0);
  let amount = Math.round((suitValue * pct) / 100);
  const minFee = rule.min_fee == null ? null : Number(rule.min_fee);
  const maxFee = rule.max_fee == null ? null : Number(rule.max_fee);
  if (minFee != null) amount = Math.max(minFee, amount);
  if (maxFee != null) amount = Math.min(maxFee, amount);
  return {
    amount,
    detail: `${pct}% of suit value${minFee != null ? ` (min ${minFee})` : ""}${maxFee != null ? ` (max ${maxFee})` : ""}`,
  };
}

export function formatCourtFeeEstimate(rules, intake, formatCurrency) {
  const missing = missingCourtFeeFields(intake);
  if (missing.length) {
    return {
      ok: false,
      html: `<strong>Need more information:</strong> ${escape(missing.join("; "))}.`,
      missing,
    };
  }

  const resolved = resolveRule(rules, intake);
  if (resolved.error) {
    return { ok: false, html: `<strong>Configuration gap:</strong> ${escape(resolved.error)}`, missing: [] };
  }

  const { state, rule } = resolved;
  const caseLabel = caseTypeLabel(rules, intake.caseType);
  const fee = computeOrientationFee(rule, intake.suitValue);
  const sectionHint = rule.section_hint || state.section_hint_default || "Verify applicable section";
  const scheduleHint = rule.schedule_hint || state.schedule_hint_default || "Verify applicable schedule";
  const stateCaveats = (state.caveats || []).map((item) => `<li>${escape(item)}</li>`).join("");
  const feeLine =
    fee.amount == null
      ? `<div><strong>Court fee amount:</strong> Not auto-computed — verify Schedule for this relief.</div>`
      : `<div><strong>Orientation court fee:</strong> ${escape(formatCurrency(fee.amount))} <em>(${escape(fee.detail)})</em></div>`;

  const html = `
    <div class="legal-tool-output-card">
      <div><strong>State:</strong> ${escape(state.label)}</div>
      <div><strong>Suit / case type:</strong> ${escape(caseLabel)}</div>
      <div><strong>Suit value:</strong> ${escape(formatCurrency(intake.suitValue))}</div>
      <div><strong>Applicable law:</strong> ${escape(state.act)}</div>
      <div><strong>Relevant provision (verify):</strong> ${escape(sectionHint)}</div>
      <div><strong>Schedule (verify):</strong> ${escape(scheduleHint)}</div>
      <div><strong>Court fee formula:</strong> ${escape(rule.formula_label || "Verify Act schedule")}</div>
      ${feeLine}
      <div><strong>Valuation notes:</strong> ${escape(rule.valuation_notes || "")}</div>
      ${intake.notes ? `<div><strong>Your notes:</strong> ${escape(intake.notes)}</div>` : ""}
      <div class="legal-tool-output-block">
        <strong>State-wise caveats</strong>
        <ul>${stateCaveats}</ul>
      </div>
      <div class="legal-tool-disclaimer"><strong>Disclaimer:</strong> ${escape(rules.disclaimer)}</div>
    </div>
  `;

  return {
    ok: true,
    html,
    missing: [],
    state,
    rule,
    caseLabel,
    fee,
  };
}

export function buildCourtFeeAiPrompt(rules, formatCurrency) {
  const intake = readCourtFeeIntake();
  const missing = missingCourtFeeFields(intake);
  if (missing.length) {
    return {
      ok: false,
      missing,
      prompt: "",
      message: `Before opening AI, complete: ${missing.join("; ")}.`,
    };
  }

  const estimate = formatCourtFeeEstimate(rules, intake, formatCurrency);
  if (!estimate.ok) {
    return { ok: false, missing: [], prompt: "", message: "Court-fee configuration gap — update rules JSON." };
  }

  const { state, rule, caseLabel, fee } = estimate;
  const prompt = [
    "Prepare a Court Fee decision-support note under Indian law for this filing orientation.",
    `State/UT: ${state.label}.`,
    `Case type: ${caseLabel}.`,
    `Suit value: ${formatCurrency(intake.suitValue)}.`,
    intake.notes ? `Additional user notes: ${intake.notes}.` : "",
    `Applicable Act (from rules config): ${state.act}.`,
    `Section hint to verify: ${rule.section_hint || state.section_hint_default}.`,
    `Schedule hint to verify: ${rule.schedule_hint || state.schedule_hint_default}.`,
    `Formula note: ${rule.formula_label}.`,
    `Valuation notes: ${rule.valuation_notes}.`,
    fee.amount == null
      ? "Do not invent a precise rupee fee; explain how to locate the correct Schedule entry."
      : `Orientation amount from config engine: ${formatCurrency(fee.amount)} (${fee.detail}). Treat as non-binding.`,
    `State caveats: ${(state.caveats || []).join(" | ")}`,
    `Common caveats: ${(rules.common_caveats || []).join(" | ")}`,
    "Structure the answer as: State, Suit, Suit Value, Applicable Law, Relevant Provision, Schedule, Court Fee, Calculation, Notes, Disclaimer.",
    "Always say final fee depends on pleadings and valuation adopted by the Court.",
    "Do not discuss GST refunds or CGST Section 54 unless asked.",
  ]
    .filter(Boolean)
    .join("\n");

  return { ok: true, missing: [], prompt, message: "" };
}
