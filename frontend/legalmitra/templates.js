import {
  apiRequest,
  buildHeaders,
  getConfiguredApiBaseUrl,
  getAccessToken,
} from "../shared/api-client.js";

const APP_KEY = "legalmitra";
const templateList = document.getElementById("template-list");
const templateDetail = document.getElementById("template-detail");
const templateLibraryStatus = document.getElementById("template-library-status");
const reloadTemplatesButton = document.getElementById("reload-templates");
const govtFormUpload = document.getElementById("govt-form-upload");
let templateStrategyById = new Map();
let activeTemplate = null;
const TEMPLATE_CHAT_HANDOFF_KEY = "legalmitra_template_chat_handoff_v1";
const PLAN_ORDER = {
  starter: 0,
  growth: 1,
  professional: 2,
};
const PLAN_DETAILS = {
  starter: {
    label: "Starter",
    limit: "Template browsing, basic fill/preview, 5 templates/month, and limited research capacity.",
  },
  growth: {
    label: "Growth",
    limit: "AI template review, missing clause checks, drafting improvement, 30 templates/month, and 150-day retained history.",
  },
  professional: {
    label: "Professional",
    limit: "Advanced AI template review, official form processing, higher upload capacity, 200 templates/month, and 300-day retained history.",
  },
};
let currentPlan = "starter";
let hasPrivilegedUsageAccess = false;

function normalizePlan(value) {
  const tier = String(value || "free").trim().toLowerCase();
  if (["pro", "popular", "professional"].includes(tier)) return "professional";
  if (["basic", "growth"].includes(tier)) return "growth";
  return "starter";
}

function canUsePlan(requiredPlan) {
  if (hasPrivilegedUsageAccess) return true;
  return PLAN_ORDER[currentPlan] >= PLAN_ORDER[requiredPlan];
}

function showUpgradePrompt({
  feature = "AI template review",
  requiredPlan = "growth",
  reason = "",
} = {}) {
  if (hasPrivilegedUsageAccess) return;
  const existing = document.getElementById("upgrade-prompt");
  existing?.remove();
  const required = PLAN_DETAILS[requiredPlan] || PLAN_DETAILS.growth;
  const current = PLAN_DETAILS[currentPlan] || PLAN_DETAILS.starter;
  const modal = document.createElement("div");
  modal.className = "legal-upgrade-overlay";
  modal.id = "upgrade-prompt";
  modal.innerHTML = `
    <section class="legal-upgrade-modal" role="dialog" aria-modal="true" aria-labelledby="upgrade-title">
      <button class="legal-upgrade-close" type="button" data-upgrade-close aria-label="Close upgrade prompt">x</button>
      <span>Upgrade required</span>
      <h2 id="upgrade-title">${escapeHtml(feature)} is available in ${escapeHtml(required.label)}.</h2>
      <p>${escapeHtml(reason || `Your current ${current.label} plan does not include this feature.`)}</p>
      <div class="legal-upgrade-current">
        <strong>Your current plan: ${escapeHtml(current.label)}</strong>
        <small>${escapeHtml(current.limit)}</small>
      </div>
      <div class="legal-upgrade-current recommended">
        <strong>Upgrade to: ${escapeHtml(required.label)}</strong>
        <small>${escapeHtml(required.limit)}</small>
      </div>
      <div class="legal-upgrade-actions">
        <a href="./pricing.html">View plans</a>
        <a href="./contact.html">Contact LegalMitra</a>
      </div>
    </section>
  `;
  modal.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (target === modal || target?.closest("[data-upgrade-close]")) {
      modal.remove();
    }
  });
  document.body.appendChild(modal);
}

async function loadCurrentPlan() {
  if (!getAccessToken()) {
    currentPlan = "starter";
    hasPrivilegedUsageAccess = false;
    return;
  }
  const result = await apiRequest(APP_KEY, "/api/v1/users/me/usage", { method: "GET" });
  if (result.ok) {
    hasPrivilegedUsageAccess = Boolean(result.payload?.privileged_usage_access);
    currentPlan = hasPrivilegedUsageAccess
      ? "professional"
      : normalizePlan(result.payload?.effective_tier || result.payload?.tier);
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeFieldType(type) {
  const normalized = String(type || "text").toLowerCase();
  if (["textarea", "number", "date", "email"].includes(normalized)) return normalized;
  return "text";
}

function renderFieldControl(field) {
  const fieldId = String(field.id || "").trim();
  const fieldType = normalizeFieldType(field.type);
  const label = escapeHtml(field.label || fieldId);
  const inputName = escapeHtml(fieldId);
  const required = field.required ? "required" : "";
  const placeholder = escapeHtml(field.placeholder || `Enter ${field.label || fieldId}`);
  const helpText = `${field.required ? "Required" : "Optional"} - ${fieldType}`;

  if (fieldType === "textarea") {
    return `
      <label class="legal-template-field">
        <span>${label}${field.required ? " *" : ""}</span>
        <small>${escapeHtml(helpText)}</small>
        <textarea name="${inputName}" rows="4" placeholder="${placeholder}" ${required}></textarea>
      </label>
    `;
  }

  return `
    <label class="legal-template-field">
      <span>${label}${field.required ? " *" : ""}</span>
      <small>${escapeHtml(helpText)}</small>
      <input name="${inputName}" type="${fieldType}" placeholder="${placeholder}" ${required}>
    </label>
  `;
}

function collectTemplateFields() {
  const form = document.getElementById("template-generate-form");
  if (!(form instanceof HTMLFormElement)) return {};
  const fields = {};
  const data = new FormData(form);
  for (const [key, value] of data.entries()) {
    fields[key] = String(value || "").trim();
  }
  return fields;
}

function buildTemplateChatPrompt() {
  const fields = collectTemplateFields();
  const preview = String(document.getElementById("template-preview-output")?.textContent || "").trim();
  const fieldLines = Object.entries(fields)
    .filter(([, value]) => String(value || "").trim())
    .map(([key, value]) => `- ${key}: ${value}`);
  const templateName = activeTemplate?.name || activeTemplate?.template_id || "selected template";
  const parts = [
    `Help me review and improve this ${templateName} for Indian law use.`,
    "Please check completeness, missing clauses, risk points, drafting quality, and practical next steps.",
  ];
  if (fieldLines.length) {
    parts.push("", "Filled template inputs:", fieldLines.join("\n"));
  }
  if (preview && !preview.startsWith("Generated document preview will appear")) {
    parts.push("", "Generated draft preview:", preview.slice(0, 6000));
  }
  return parts.join("\n");
}

function sendTemplateToChat() {
  if (!activeTemplate?.template_id) return;
  if (getAccessToken() && !canUsePlan("growth")) {
    showUpgradePrompt({
      feature: "AI template review",
      requiredPlan: "growth",
      reason: "Starter lets you browse, fill, preview, and download limited templates. Growth unlocks AI review for missing clauses, risk points, drafting quality, and practical next steps.",
    });
    setTemplateStatus("AI template review is available in Growth and Professional.", "warning");
    return;
  }
  const prompt = buildTemplateChatPrompt();
  const handoff = {
    template_id: activeTemplate.template_id,
    template_name: activeTemplate.name || activeTemplate.template_id,
    query: prompt,
    mode: "drafting",
    created_at: new Date().toISOString(),
  };
  sessionStorage.setItem(TEMPLATE_CHAT_HANDOFF_KEY, JSON.stringify(handoff));
  localStorage.setItem(TEMPLATE_CHAT_HANDOFF_KEY, JSON.stringify(handoff));
  const chatUrl = `./chat.html?handoff=template&mode=drafting&auto=0&q=${encodeURIComponent(prompt.slice(0, 1800))}`;
  if (getAccessToken()) {
    window.location.href = chatUrl;
  } else {
    window.location.href = `./login.html?return=${encodeURIComponent(chatUrl)}`;
  }
}

function setTemplateStatus(message, kind = "info") {
  const status = document.getElementById("template-generate-status");
  if (!status) return;
  status.textContent = message;
  status.dataset.kind = kind;
}

function requireTemplateLogin() {
  if (getAccessToken()) return false;
  setTemplateStatus("Please sign in before generating or downloading a legal draft.", "error");
  window.location.href = `./login.html?return=${encodeURIComponent("./templates.html")}`;
  return true;
}

function renderTemplateDetail(template) {
  if (!templateDetail || !template) return;
  activeTemplate = template;
  const strategy = templateStrategyById.get(template.template_id);
  const fields = Array.isArray(template.fields) ? template.fields : [];
  const tags = Array.isArray(template.tags) ? template.tags : [];
  const acts = Array.isArray(template.act) ? template.act : [];
  const status = strategy?.status || "legacy_catalog_template";

  templateDetail.innerHTML = `
    <span>${escapeHtml(template.category || "template")} - ${escapeHtml(status.replaceAll("_", " "))}</span>
    <h3>${escapeHtml(template.name || strategy?.title || template.template_id)}</h3>
    <p>${escapeHtml(template.description || "No description available.")}</p>
    <div class="legal-template-meta">
      ${tags.slice(0, 6).map((tag) => `<small>${escapeHtml(tag)}</small>`).join("")}
      ${acts.slice(0, 4).map((act) => `<small>${escapeHtml(act)}</small>`).join("")}
    </div>
    <div class="legal-template-fields">
      <strong>Required Inputs</strong>
      ${
        fields.length
          ? `<form class="legal-template-generate-form" id="template-generate-form">
              ${fields.slice(0, 24).map(renderFieldControl).join("")}
            </form>`
          : "<p>No field specification available for this template.</p>"
      }
    </div>
    <div class="legal-template-actions">
      <button type="button" id="preview-template-draft">Preview draft</button>
      <button type="button" id="download-template-pdf">Download PDF</button>
      <button type="button" id="ask-ai-about-template">Ask AI about this template <small>Growth+</small></button>
    </div>
    <p class="legal-template-generate-status" id="template-generate-status">Fill the fields and click Preview draft.</p>
    <section class="legal-template-preview" aria-label="Generated document preview">
      <div>
        <strong>Document Preview</strong>
        <small>Review before download. LegalMitra drafts still require professional human review.</small>
      </div>
      <pre id="template-preview-output">Generated document preview will appear here after you click Preview draft.</pre>
    </section>
  `;
}

async function previewActiveTemplate() {
  if (!activeTemplate?.template_id) return;
  if (requireTemplateLogin()) return;
  const form = document.getElementById("template-generate-form");
  if (form instanceof HTMLFormElement && !form.reportValidity()) {
    setTemplateStatus("Complete the required fields before generating the draft.", "error");
    return;
  }
  setTemplateStatus("Generating draft preview...", "info");
  const result = await apiRequest(APP_KEY, "/api/v1/v2/templates/render", {
    method: "POST",
    body: JSON.stringify({
      template_id: activeTemplate.template_id,
      fields: collectTemplateFields(),
    }),
    timeoutMs: 20000,
  });

  if (!result.ok) {
    setTemplateStatus(result.payload?.detail || `Could not generate draft. HTTP ${result.status}`, "error");
    return;
  }

  const output = document.getElementById("template-preview-output");
  if (output) {
    output.textContent = result.payload?.rendered_document || "No draft returned.";
  }
  const missing = result.payload?.validation?.missing_required_fields || [];
  if (Array.isArray(missing) && missing.length) {
    setTemplateStatus(`Draft generated with ${missing.length} missing required field(s). Complete them before final use.`, "warning");
  } else {
    setTemplateStatus("Draft generated successfully. Review it before download.", "success");
  }
}

async function downloadActiveTemplatePdf() {
  if (!activeTemplate?.template_id) return;
  if (requireTemplateLogin()) return;
  const form = document.getElementById("template-generate-form");
  if (form instanceof HTMLFormElement && !form.reportValidity()) {
    setTemplateStatus("Complete the required fields before downloading the PDF.", "error");
    return;
  }
  setTemplateStatus("Preparing PDF download...", "info");
  const response = await fetch(`${getConfiguredApiBaseUrl()}/api/v1/v2/templates/render-pdf`, {
    method: "POST",
    headers: buildHeaders(APP_KEY),
    body: JSON.stringify({
      template_id: activeTemplate.template_id,
      fields: collectTemplateFields(),
    }),
  });

  if (!response.ok) {
    let detail = `Could not download PDF. HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload?.detail || detail;
    } catch {
      // Keep the HTTP message when the server returns non-JSON.
    }
    setTemplateStatus(detail, "error");
    return;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${activeTemplate.template_id || "legalmitra-template"}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setTemplateStatus("PDF download started.", "success");
}

function renderTemplateList(templates) {
  if (!templateList) return;
  const launchIds = new Set(templateStrategyById.keys());
  const ordered = [...templates].sort((a, b) => {
    const aLaunch = launchIds.has(a.template_id) ? 0 : 1;
    const bLaunch = launchIds.has(b.template_id) ? 0 : 1;
    if (aLaunch !== bLaunch) return aLaunch - bLaunch;
    return String(a.name || "").localeCompare(String(b.name || ""));
  });

  templateList.innerHTML = ordered.slice(0, 80).map((template, index) => {
    const strategy = templateStrategyById.get(template.template_id);
    return `
      <button type="button" data-template-id="${escapeHtml(template.template_id)}" class="${index === 0 ? "active" : ""}">
        <strong>${escapeHtml(template.name || strategy?.title || template.template_id)}</strong>
        <span>${escapeHtml(strategy?.status?.replaceAll("_", " ") || template.category || "legacy template")}</span>
      </button>
    `;
  }).join("");

  if (ordered[0]) {
    loadTemplateDetailById(ordered[0].template_id, ordered[0]);
  }
}

async function loadTemplateDetailById(templateId, fallbackTemplate = null) {
  if (!templateId) return;
  const result = await apiRequest(APP_KEY, `/api/v1/v2/templates/${encodeURIComponent(templateId)}`, {
    method: "GET",
    timeoutMs: 15000,
  });

  if (result.ok) {
    renderTemplateDetail(result.payload?.template || result.payload);
  } else if (fallbackTemplate) {
    renderTemplateDetail(fallbackTemplate);
    setTemplateStatus("Template detail API failed; showing limited catalog fields.", "warning");
  } else if (templateDetail) {
    templateDetail.innerHTML = `
      <span>Template unavailable</span>
      <h3>Could not load template details</h3>
      <p>${escapeHtml(result.payload?.detail || "Could not load template detail from backend.")}</p>
    `;
  }
}

async function loadTemplateLibrary() {
  if (!templateList || !templateLibraryStatus) return;
  await loadCurrentPlan();
  templateLibraryStatus.textContent = "Loading templates from backend...";
  templateList.innerHTML = "";

  const [strategyResult, templatesResult] = await Promise.all([
    apiRequest(APP_KEY, "/api/v1/legalmitra/template-strategy", { method: "GET" }),
    apiRequest(APP_KEY, "/api/v1/v2/templates", { method: "GET", timeoutMs: 15000 }),
  ]);

  const launchTemplates = Array.isArray(strategyResult.payload?.launch_templates)
    ? strategyResult.payload.launch_templates
    : [];
  templateStrategyById = new Map(launchTemplates.map((item) => [item.template_id, item]));

  if (!templatesResult.ok) {
    templateLibraryStatus.textContent = `Template API unavailable: HTTP ${templatesResult.status}`;
    templateList.innerHTML = `
      <p class="legal-template-empty">Check Backend API base URL and confirm the backend is running at ${escapeHtml(getConfiguredApiBaseUrl())}.</p>
    `;
    return;
  }

  const templates = Array.isArray(templatesResult.payload?.templates)
    ? templatesResult.payload.templates
    : Array.isArray(templatesResult.payload?.items)
      ? templatesResult.payload.items
      : [];
  templateLibraryStatus.textContent = `${templates.length} template(s) loaded. Launch-grade templates are shown first.`;
  renderTemplateList(templates);
}

templateList?.addEventListener("click", async (event) => {
  const clicked = event.target;
  if (!(clicked instanceof Element)) return;
  const target = clicked.closest("[data-template-id]");
  if (!(target instanceof HTMLElement)) return;

  templateList.querySelectorAll("[data-template-id]").forEach((node) => node.classList.remove("active"));
  target.classList.add("active");

  const templateId = target.getAttribute("data-template-id");
  if (!templateId) return;
  await loadTemplateDetailById(templateId);
});

reloadTemplatesButton?.addEventListener("click", loadTemplateLibrary);

templateDetail?.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (target?.closest("#preview-template-draft")) {
    previewActiveTemplate();
  }
  if (target?.closest("#download-template-pdf")) {
    downloadActiveTemplatePdf();
  }
  if (target?.closest("#ask-ai-about-template")) {
    sendTemplateToChat();
  }
});

govtFormUpload?.addEventListener("click", () => {
  if (hasPrivilegedUsageAccess) {
    govtFormUpload.textContent = "Platform owner access enabled";
    setTemplateStatus("Platform owner/admin access bypasses Professional plan restrictions for E2E verification.", "success");
    return;
  }
  govtFormUpload.textContent = "Available in Professional plan";
  showUpgradePrompt({
    feature: "Government form auto-fill",
    requiredPlan: "professional",
    reason: "Official PDF form processing requires Professional because it uses higher document capacity and review controls.",
  });
});

loadTemplateLibrary();
