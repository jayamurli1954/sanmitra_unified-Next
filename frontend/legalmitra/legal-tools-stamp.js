/**
 * Stamp Duty & Registration — intake + practical checklist helpers.
 * Orientation only; verify state law, guidance value, and registry practice.
 */

export const STAMP_DUTY_CHECKLIST = [
  {
    section: "Before registration",
    items: [
      "Verify market value (Guidance Value / Circle Rate)",
      "Verify agreed sale consideration",
      "Check applicable stamp duty rate",
      "Check applicable registration fee",
      "Confirm concessions (e.g. women buyers in some states)",
      "Ensure property is free from legal disputes",
      "Verify seller title documents",
      "Check Encumbrance Certificate",
      "Verify latest property tax receipts",
      "Verify Khata / Mutation records (where applicable)",
    ],
  },
  {
    section: "Documents required",
    items: [
      "Sale Deed draft ready",
      "Identity proof of buyer",
      "Identity proof of seller",
      "PAN cards",
      "Aadhaar (where applicable)",
      "Photographs",
      "Address proof",
      "Property tax receipt",
      "Encumbrance Certificate",
      "Khata certificate / extract (if applicable)",
      "NOC (if required)",
      "Power of Attorney (if applicable)",
      "Builder documents (for new property)",
    ],
  },
  {
    section: "Before signing",
    items: [
      "Names correct",
      "Property description correct",
      "Survey / Khata numbers correct",
      "Extent / area and boundaries correct",
      "Sale consideration and payment details correct",
      "Witness details ready",
    ],
  },
  {
    section: "At registration office",
    items: [
      "Stamp duty paid",
      "Registration charges paid",
      "Original documents presented",
      "Biometric / photograph / signatures completed",
      "Witness signatures completed",
      "Registration completed",
    ],
  },
  {
    section: "After registration",
    items: [
      "Collect registered Sale Deed",
      "Verify document number",
      "Apply for Mutation / Khata transfer",
      "Update municipal / property tax records",
      "Preserve original documents safely",
    ],
  },
];

/** Indicative orientation rates only — not official tariffs. */
export const STAMP_DUTY_STATE_DEFAULTS = {
  karnataka: { stamp: 5, registration: 1, label: "Karnataka" },
  maharashtra: { stamp: 6, registration: 1, label: "Maharashtra" },
  delhi: { stamp: 6, registration: 1, label: "Delhi" },
  "tamil-nadu": { stamp: 7, registration: 1, label: "Tamil Nadu" },
  telangana: { stamp: 6, registration: 0.5, label: "Telangana" },
  "andhra-pradesh": { stamp: 6, registration: 0.5, label: "Andhra Pradesh" },
  other: { stamp: 5, registration: 1, label: "Other / confirm state schedule" },
};

export function stampDutyToolBodyHtml() {
  const checklistHtml = STAMP_DUTY_CHECKLIST.map((group, groupIndex) => {
    const items = group.items
      .map((label, itemIndex) => {
        const id = `stamp-check-${groupIndex}-${itemIndex}`;
        return `<label class="legal-tool-check"><input type="checkbox" id="${id}" data-stamp-check="${id}"><span>${label}</span></label>`;
      })
      .join("");
    return `<div class="legal-tool-check-group"><strong>${group.section}</strong>${items}</div>`;
  }).join("");

  return `
    <p class="legal-tool-intake-lead">
      Stamp duty is a <strong>state</strong> tax on property instruments; registration charges are fees for recording the transfer.
      LegalMitra needs the facts below before estimating or opening AI — rates and concessions vary by state.
    </p>
    <div class="legal-tool-intake-grid">
      <label>State
        <select id="tool-stamp-state">
          <option value="">Select state…</option>
          <option value="karnataka">Karnataka</option>
          <option value="maharashtra">Maharashtra</option>
          <option value="delhi">Delhi</option>
          <option value="tamil-nadu">Tamil Nadu</option>
          <option value="telangana">Telangana</option>
          <option value="andhra-pradesh">Andhra Pradesh</option>
          <option value="other">Other (confirm official schedule)</option>
        </select>
      </label>
      <label>Property / instrument type
        <select id="tool-stamp-property-type">
          <option value="">Select type…</option>
          <option value="sale">Sale of immovable property</option>
          <option value="gift">Gift deed</option>
          <option value="lease">Lease</option>
          <option value="builder">New builder / apartment purchase</option>
          <option value="other">Other instrument</option>
        </select>
      </label>
      <label>Sale consideration (₹)
        <input id="tool-stamp-sale" type="number" min="0" placeholder="Example: 8000000">
      </label>
      <label>Guidance / circle rate (₹)
        <input id="tool-stamp-guidance" type="number" min="0" placeholder="Example: 8200000">
      </label>
      <label>Buyer category
        <select id="tool-stamp-buyer">
          <option value="general">General</option>
          <option value="woman">Woman buyer (check state concession)</option>
          <option value="joint-woman">Joint with woman buyer</option>
          <option value="other-concession">Other concession category</option>
        </select>
      </label>
      <label>Stamp duty rate % (indicative)
        <input id="tool-stamp-rate" type="number" min="0" step="0.1" placeholder="Auto-fills from state">
      </label>
      <label>Registration fee % (indicative)
        <input id="tool-stamp-reg-rate" type="number" min="0" step="0.1" placeholder="Auto-fills from state">
      </label>
      <label>City / locality (optional)
        <input id="tool-stamp-city" maxlength="80" placeholder="Example: Bengaluru">
      </label>
    </div>
    <button type="button" data-tool-action="stamp-duty">Estimate duty &amp; refresh checklist</button>
    <div class="legal-tool-result" id="tool-result">
      Enter <strong>state</strong>, <strong>sale consideration</strong> and/or <strong>guidance value</strong>, then estimate.
      Duty is usually computed on the <strong>higher</strong> of sale price and guidance value.
    </div>
    <div class="legal-tool-checklist" id="tool-stamp-checklist">
      <h4>Practical registration checklist</h4>
      <p>Tick items as you verify them. Unchecked items are sent to LegalMitra AI as open follow-ups.</p>
      ${checklistHtml}
    </div>
  `;
}

export function readStampDutyIntake() {
  const stateKey = String(document.getElementById("tool-stamp-state")?.value || "").trim();
  const defaults = STAMP_DUTY_STATE_DEFAULTS[stateKey] || null;
  const sale = Number(document.getElementById("tool-stamp-sale")?.value || 0);
  const guidance = Number(document.getElementById("tool-stamp-guidance")?.value || 0);
  const stampRateInput = document.getElementById("tool-stamp-rate");
  const regRateInput = document.getElementById("tool-stamp-reg-rate");
  let stampRate = Number(stampRateInput?.value || 0);
  let regRate = Number(regRateInput?.value || 0);
  if (defaults && !stampRate && stampRateInput) {
    stampRateInput.value = String(defaults.stamp);
    stampRate = defaults.stamp;
  }
  if (defaults && !regRate && regRateInput) {
    regRateInput.value = String(defaults.registration);
    regRate = defaults.registration;
  }
  return {
    stateKey,
    stateLabel: defaults?.label || (stateKey ? stateKey : ""),
    propertyType: String(document.getElementById("tool-stamp-property-type")?.value || "").trim(),
    sale,
    guidance,
    dutyBase: Math.max(sale || 0, guidance || 0),
    buyer: String(document.getElementById("tool-stamp-buyer")?.value || "general"),
    stampRate,
    regRate,
    city: String(document.getElementById("tool-stamp-city")?.value || "").trim(),
  };
}

export function missingStampDutyFields(intake = readStampDutyIntake()) {
  const missing = [];
  if (!intake.stateKey) missing.push("State");
  if (!intake.propertyType) missing.push("Property / instrument type");
  if (!intake.sale && !intake.guidance) missing.push("Sale consideration and/or Guidance value");
  if (!intake.stampRate) missing.push("Stamp duty rate %");
  return missing;
}

export function collectStampDutyChecklistStatus() {
  const open = [];
  const done = [];
  STAMP_DUTY_CHECKLIST.forEach((group, groupIndex) => {
    group.items.forEach((label, itemIndex) => {
      const id = `stamp-check-${groupIndex}-${itemIndex}`;
      const checked = Boolean(document.getElementById(id)?.checked);
      const row = `${group.section}: ${label}`;
      if (checked) done.push(row);
      else open.push(row);
    });
  });
  return { open, done };
}

export function formatStampDutyEstimate(intake, formatCurrency) {
  const missing = missingStampDutyFields(intake);
  if (missing.length) {
    return {
      ok: false,
      html: `<strong>Need more information:</strong> ${missing.join("; ")}.`,
      missing,
    };
  }
  const stampAmount = (intake.dutyBase * intake.stampRate) / 100;
  const regAmount = (intake.dutyBase * intake.regRate) / 100;
  const baseLabel =
    intake.sale && intake.guidance
      ? `higher of sale ${formatCurrency(intake.sale)} and guidance ${formatCurrency(intake.guidance)}`
      : formatCurrency(intake.dutyBase);
  const concessionNote =
    intake.buyer === "woman" || intake.buyer === "joint-woman"
      ? " Buyer category may attract a state concession — verify the current state schedule before payment."
      : "";
  return {
    ok: true,
    html: [
      `<strong>Indicative estimate (${escape(intake.stateLabel)}):</strong>`,
      `Duty base ${baseLabel}.`,
      `Stamp duty ≈ <strong>${formatCurrency(stampAmount)}</strong> at ${intake.stampRate}%.`,
      `Registration ≈ <strong>${formatCurrency(regAmount)}</strong> at ${intake.regRate}%.`,
      `Combined orientation ≈ <strong>${formatCurrency(stampAmount + regAmount)}</strong>.`,
      concessionNote,
      " Verify cess/surcharge/transfer duty, under-valuation risk, and official guidance value before registration.",
    ].join(" "),
    missing: [],
    stampAmount,
    regAmount,
  };
}

function escape(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function buildStampDutyAiPrompt(formatCurrency) {
  const intake = readStampDutyIntake();
  const missing = missingStampDutyFields(intake);
  const checklist = collectStampDutyChecklistStatus();
  const estimate = missing.length ? null : formatStampDutyEstimate(intake, formatCurrency);

  if (missing.length) {
    return {
      ok: false,
      missing,
      prompt: "",
      message: `Before opening AI, complete: ${missing.join("; ")}.`,
    };
  }

  const openTop = checklist.open.slice(0, 12);
  const prompt = [
    "Prepare a practical Stamp Duty and Registration Charges checklist under Indian law for this property transaction.",
    "Explain briefly: what stamp duty is (state tax), what registration charges are, and that duty is usually on the higher of sale consideration and guidance/circle rate.",
    `State: ${intake.stateLabel}.`,
    intake.city ? `City/locality: ${intake.city}.` : "",
    `Instrument/property type: ${intake.propertyType}.`,
    `Sale consideration: ${intake.sale ? formatCurrency(intake.sale) : "not provided"}.`,
    `Guidance/circle rate: ${intake.guidance ? formatCurrency(intake.guidance) : "not provided"}.`,
    `Duty base used for orientation: ${formatCurrency(intake.dutyBase)}.`,
    `Buyer category: ${intake.buyer}.`,
    `Indicative stamp duty rate: ${intake.stampRate}%; registration fee rate: ${intake.regRate}%.`,
    estimate?.ok
      ? `Orientation amounts — stamp ≈ ${formatCurrency(estimate.stampAmount)}, registration ≈ ${formatCurrency(estimate.regAmount)}.`
      : "",
    openTop.length
      ? `Unchecked checklist items still open for the user:\n- ${openTop.join("\n- ")}`
      : "User marked the on-screen checklist items as reviewed.",
    "Structure the answer as: (1) short definitions, (2) calculation note, (3) charges to verify by state, (4) documents, (5) before signing / at registry / after registration steps, (6) quick tick checklist.",
    "Do not invent a binding official rate. Flag that state schedules, concessions, cess, and under-valuation rules must be verified.",
    "Do not discuss GST refunds or CGST Section 54 unless asked.",
  ]
    .filter(Boolean)
    .join("\n");

  return { ok: true, missing: [], prompt, message: "" };
}

export function bindStampDutyStateDefaults() {
  const stateSelect = document.getElementById("tool-stamp-state");
  if (!stateSelect || stateSelect.dataset.bound === "1") return;
  stateSelect.dataset.bound = "1";
  stateSelect.addEventListener("change", () => {
    const defaults = STAMP_DUTY_STATE_DEFAULTS[stateSelect.value];
    if (!defaults) return;
    const stampRate = document.getElementById("tool-stamp-rate");
    const regRate = document.getElementById("tool-stamp-reg-rate");
    if (stampRate) stampRate.value = String(defaults.stamp);
    if (regRate) regRate.value = String(defaults.registration);
  });
}
