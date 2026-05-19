import {
  apiRequest,
  clearAccessToken,
  getAccessToken,
  getConfiguredApiBaseUrl,
  loadHealth,
  loadModules,
  moduleItemsFromPayload,
  renderModuleState,
  renderJson,
  setAccessToken,
  setConfiguredApiBaseUrl,
  statusLabel,
} from "../shared/api-client.js";

const APP_KEY = "legalmitra";
const IS_CHAT_PAGE = document.body?.dataset?.legalPage === "chat";

const fallbackModules = [
  { module_key: "legal", display_name: "LegalMitra Legal Workflow", frontend_path: "/legal", nav_group: "Legal", enabled: true },
  { module_key: "rag", display_name: "Legal Research RAG", frontend_path: "/legal/research", nav_group: "Legal", enabled: true },
  { module_key: "compliance", display_name: "Compliance Calendar", frontend_path: "/legal/compliance", nav_group: "Compliance", enabled: true },
  { module_key: "legal_ai", display_name: "Legal AI Assistant", frontend_path: "/legal/assistant", nav_group: "AI Assistant", enabled: false },
  { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
];

const nav = document.getElementById("nav");
const moduleList = document.getElementById("module-list");
const apiOutput = document.getElementById("api-output");
const healthPill = document.getElementById("health-pill");
const moduleState = document.getElementById("module-state");
const apiBaseInput = document.getElementById("api-base");
const tokenInput = document.getElementById("access-token");
const loginEmailInput = document.getElementById("login-email");
const loginPasswordInput = document.getElementById("login-password");
const outputModeInput = document.getElementById("legal-output-mode");
const queryInput = document.getElementById("query");
const followUpInput = document.getElementById("follow-up-query");
const answerPanel = document.getElementById("legal-answer-panel");
const usageCounter = document.getElementById("usage-counter");
const workspaceShell = document.getElementById("legal-workspace-shell");
const historyList = document.getElementById("history-list");
const historyStatus = document.getElementById("history-status");
const refreshHistoryButton = document.getElementById("refresh-history");
const uploadHistoryList = document.getElementById("upload-history-list");
const uploadHistoryStatus = document.getElementById("upload-history-status");
const authSignIn = document.getElementById("auth-sign-in");
const authUserMenu = document.getElementById("legal-user-menu");
const authUserLabel = document.getElementById("auth-user-label");
const logoutButton = document.getElementById("logout-legalmitra");
const solutionsList = document.getElementById("solutions-list");
const faqList = document.getElementById("faq-list");
const solutionsMenu = document.getElementById("solutions-menu");
const solutionsToggle = document.getElementById("solutions-toggle");
const templateList = document.getElementById("template-list");
const templateDetail = document.getElementById("template-detail");
const templateLibraryStatus = document.getElementById("template-library-status");
const reloadTemplatesButton = document.getElementById("reload-templates");
const legalToolPanel = document.getElementById("legal-tool-panel");
const majorCasesList = document.getElementById("major-cases-list");
const legalNewsList = document.getElementById("legal-news-list");
const refreshMajorCasesButton = document.getElementById("refresh-major-cases");
const refreshLegalNewsButton = document.getElementById("refresh-legal-news");
let lastAnswerText = "";
let lastAnswerMeta = null;
let templateStrategyById = new Map();
let activeSpeech = null;
const ANSWER_FEEDBACK_KEY = "legalmitra_answer_feedback_v1";
const TEMPLATE_CHAT_HANDOFF_KEY = "legalmitra_template_chat_handoff_v1";
let currentPlan = "starter";
let hasPrivilegedUsageAccess = false;

const PLAN_ORDER = {
  starter: 0,
  growth: 1,
  professional: 2,
};

const PLAN_DETAILS = {
  starter: {
    label: "Starter",
    limit: "5 AI research queries/day, 5 templates/month, 10 tracker records, 30-day history retention",
  },
  growth: {
    label: "Growth",
    limit: "50 AI research queries/day, 30 templates/month, 100 tracker records, all legal tools, 150-day history retention",
  },
  professional: {
    label: "Professional",
    limit: "Unlimited research, 200 templates/month, unlimited tracker records, official form upload, 300-day history retention",
  },
};

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

function setChatWorkspaceActive(active) {
  if (!workspaceShell) return;
  workspaceShell.classList.toggle("chat-active", Boolean(active && getAccessToken()));
}

function renderSignedOutHeader() {
  authSignIn?.removeAttribute("hidden");
  if (authUserMenu) {
    authUserMenu.hidden = true;
  }
}

function renderSignedInHeader(user) {
  const name = String(user?.full_name || user?.name || user?.email || "LegalMitra user").trim();
  const role = String(user?.role || "").replaceAll("_", " ");
  if (authUserLabel) {
    authUserLabel.textContent = role ? `${name} - ${role}` : name;
  }
  authSignIn?.setAttribute("hidden", "hidden");
  if (authUserMenu) {
    authUserMenu.hidden = false;
  }
}

async function hydrateAuthHeader() {
  if (!getAccessToken()) {
    renderSignedOutHeader();
    setChatWorkspaceActive(false);
    return null;
  }

  const result = await apiRequest(APP_KEY, "/api/v1/auth/me", { method: "GET" });
  if (!result.ok) {
    clearAccessToken();
    renderSignedOutHeader();
    setChatWorkspaceActive(false);
    return null;
  }

  renderSignedInHeader(result.payload);
  return result.payload;
}

function buildChatUrl({ auto = false } = {}) {
  const params = new URLSearchParams();
  const query = String(queryInput?.value || "").trim();
  const mode = String(outputModeInput?.value || "advocate_research").trim();
  if (query) params.set("q", query);
  if (mode) params.set("mode", mode);
  if (auto) params.set("auto", "1");
  const suffix = params.toString();
  return `./chat.html${suffix ? `?${suffix}` : ""}`;
}

function redirectToLogin() {
  window.location.href = `./login.html?return=${encodeURIComponent(buildChatUrl({ auto: true }))}`;
}

function showUpgradePrompt({ feature, requiredPlan = "growth", reason = "" }) {
  if (hasPrivilegedUsageAccess) return;
  const existing = document.getElementById("upgrade-prompt");
  existing?.remove();
  const plan = PLAN_DETAILS[requiredPlan] || PLAN_DETAILS.growth;
  const current = PLAN_DETAILS[currentPlan] || PLAN_DETAILS.starter;
  const modal = document.createElement("div");
  modal.className = "legal-upgrade-overlay";
  modal.id = "upgrade-prompt";
  modal.innerHTML = `
    <section class="legal-upgrade-modal" role="dialog" aria-modal="true" aria-labelledby="upgrade-title">
      <button class="legal-upgrade-close" type="button" data-upgrade-close aria-label="Close upgrade prompt">x</button>
      <span>Upgrade required</span>
      <h2 id="upgrade-title">${escapeHtml(feature)} is available in ${escapeHtml(plan.label)}.</h2>
      <p>${escapeHtml(reason || `Your current ${current.label} plan does not include this feature.`)}</p>
      <div class="legal-upgrade-current">
        <strong>Current: ${escapeHtml(current.label)}</strong>
        <small>${escapeHtml(current.limit)}</small>
      </div>
      <div class="legal-upgrade-current recommended">
        <strong>Upgrade to: ${escapeHtml(plan.label)}</strong>
        <small>${escapeHtml(plan.limit)}</small>
      </div>
      <div class="legal-upgrade-actions">
        <a href="#pricing" data-upgrade-close>View plans</a>
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

function requirePlan(requiredPlan, feature, reason) {
  if (canUsePlan(requiredPlan)) return true;
  showUpgradePrompt({ feature, requiredPlan, reason });
  return false;
}

function loadAnswerFeedback() {
  try {
    return JSON.parse(localStorage.getItem(ANSWER_FEEDBACK_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveAnswerFeedback(feedback) {
  localStorage.setItem(ANSWER_FEEDBACK_KEY, JSON.stringify(feedback));
}

function hashText(value) {
  let hash = 0;
  const text = String(value || "");
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
  }
  return `ans_${Math.abs(hash)}`;
}

function setAnswerStatus(message) {
  const node = document.getElementById("answer-action-status");
  if (node) {
    node.textContent = message;
  }
}

function updateAnswerButtonState(action, active) {
  const button = answerPanel?.querySelector(`[data-answer-action="${action}"]`);
  if (!button) return;
  button.classList.toggle("active", active);
  button.setAttribute("aria-pressed", String(active));
}

async function persistAnswerFeedback(kind, value) {
  if (!lastAnswerMeta?.id) return;
  const feedback = loadAnswerFeedback();
  feedback[lastAnswerMeta.id] = {
    ...(feedback[lastAnswerMeta.id] || {}),
    id: lastAnswerMeta.id,
    kind,
    value,
    query: lastAnswerMeta.query,
    provider: lastAnswerMeta.provider,
    strategy: lastAnswerMeta.strategy,
    timestamp: new Date().toISOString(),
  };
  saveAnswerFeedback(feedback);

  try {
    await apiRequest(APP_KEY, "/api/v1/legalmitra/answer-feedback", {
      method: "POST",
      body: JSON.stringify({
        answer_id: lastAnswerMeta.id,
        feedback_type: kind,
        value,
        query: lastAnswerMeta.query,
        provider: lastAnswerMeta.provider,
        strategy: lastAnswerMeta.strategy,
      }),
      timeoutMs: 3000,
    });
  } catch {
    // Local feedback is retained even when the backend feedback endpoint is not available yet.
  }
}

function closeSolutionsMenu() {
  if (!solutionsMenu || !solutionsToggle) return;
  solutionsMenu.classList.remove("open");
  solutionsToggle.setAttribute("aria-expanded", "false");
}

function toggleSolutionsMenu(event) {
  if (!solutionsMenu || !solutionsToggle) return;
  event.preventDefault();
  const isOpen = solutionsMenu.classList.toggle("open");
  solutionsToggle.setAttribute("aria-expanded", String(isOpen));
}

solutionsToggle?.addEventListener("click", toggleSolutionsMenu);

solutionsMenu?.querySelectorAll(".legal-dropdown a").forEach((link) => {
  link.addEventListener("click", () => {
    closeSolutionsMenu();
  });
});

document.addEventListener("click", (event) => {
  if (!solutionsMenu || !solutionsMenu.classList.contains("open")) return;
  if (solutionsMenu.contains(event.target)) return;
  closeSolutionsMenu();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSolutionsMenu();
  }
});

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatInline(value) {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function isMarkdownTable(lines, index) {
  return (
    lines[index]?.includes("|")
    && lines[index + 1]?.includes("|")
    && /^(\s*\|?\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1] || "")
  );
}

function renderMarkdownTable(lines, startIndex) {
  const rows = [];
  let index = startIndex;
  while (index < lines.length && lines[index].includes("|")) {
    rows.push(lines[index]);
    index += 1;
  }

  const cells = (row) => row
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => formatInline(cell.trim()));

  const headers = cells(rows[0] || "");
  const bodyRows = rows.slice(2).map(cells);
  const html = `
    <div class="legal-answer-table-wrap">
      <table class="legal-answer-table">
        <thead><tr>${headers.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead>
        <tbody>
          ${bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;

  return { html, nextIndex: index };
}

function renderLegalMarkdown(text) {
  const lines = String(text || "").split(/\r?\n/);
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const raw = lines[index] || "";
    const line = raw.trim();

    if (!line) {
      index += 1;
      continue;
    }

    if (isMarkdownTable(lines, index)) {
      const table = renderMarkdownTable(lines, index);
      blocks.push(table.html);
      index = table.nextIndex;
      continue;
    }

    if (/^#{1,4}\s+/.test(line)) {
      blocks.push(`<h4>${formatInline(line.replace(/^#{1,4}\s+/, ""))}</h4>`);
      index += 1;
      continue;
    }

    if (/^\*\*.+\*\*:?\s*$/.test(line)) {
      blocks.push(`<h4>${formatInline(line.replace(/:$/, ""))}</h4>`);
      index += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test((lines[index] || "").trim())) {
        items.push(`<li>${formatInline(lines[index].trim().replace(/^\d+\.\s+/, ""))}</li>`);
        index += 1;
      }
      blocks.push(`<ol>${items.join("")}</ol>`);
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test((lines[index] || "").trim())) {
        items.push(`<li>${formatInline(lines[index].trim().replace(/^[-*]\s+/, ""))}</li>`);
        index += 1;
      }
      blocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    blocks.push(`<p>${formatInline(line)}</p>`);
    index += 1;
  }

  return blocks.join("");
}

function buildFollowUps(query, response) {
  const text = `${query || ""} ${response || ""}`.toLowerCase();
  if (text.includes("section 138") || text.includes("cheque") || text.includes("dishonour")) {
    return [
      "Prepare a Section 138 legal notice draft",
      "Create a cheque bounce complaint format",
      "Build a territorial jurisdiction checklist",
      "Give a step-by-step filing guide",
    ];
  }
  if (text.includes("quash") || text.includes("fir") || text.includes("section 528") || text.includes("section 482")) {
    return [
      "Create a quashing petition argument note",
      "List Bhajan Lal categories with examples",
      "Prepare counter-arguments for the State",
      "Draft a prayer clause for FIR quashing",
    ];
  }
  if (text.includes("gst") || text.includes("notice")) {
    return [
      "Draft a GST notice reply outline",
      "Create a document checklist",
      "Summarize limitation and hearing steps",
      "Prepare client questions before drafting",
    ];
  }
  return [
    "Make this into an advocate briefing note",
    "Create a practical checklist",
    "Add leading cases and ratios",
    "Draft the next document",
  ];
}

const legalTools = {
  "court-fee": {
    requiredPlan: "growth",
    label: "Court Fee Calculator",
    title: "Indicative civil court-fee orientation",
    query: "Calculate court fee for a civil suit in India and explain state-wise caveats",
    body: `
      <label>State or jurisdiction
        <select id="tool-state">
          <option value="karnataka">Karnataka</option>
          <option value="delhi">Delhi</option>
          <option value="maharashtra">Maharashtra</option>
          <option value="tamil-nadu">Tamil Nadu</option>
        </select>
      </label>
      <label>Claim value in rupees
        <input id="tool-amount" type="number" min="0" placeholder="Example: 500000">
      </label>
      <button type="button" data-tool-action="court-fee">Calculate indicative fee</button>
      <div class="legal-tool-result" id="tool-result">Enter a claim value to estimate a broad court-fee range. Verify the exact fee with the applicable Court Fees Act, state amendment, and court registry.</div>
    `,
  },
  "gst-finder": {
    requiredPlan: "starter",
    label: "GST Rate Finder",
    title: "GST rate and HSN/SAC lookup",
    query: "Find GST rate and HSN or SAC code checklist for an Indian business transaction",
    body: `
      <label>Goods or service
        <input id="tool-gst-query" placeholder="Example: laptop, legal services, software">
      </label>
      <button type="button" data-tool-action="gst-finder">Find indicative rate</button>
      <div class="legal-tool-result" id="tool-result">Search a term to see an indicative result and classification caution.</div>
    `,
  },
  "notice-drafter": {
    requiredPlan: "growth",
    label: "Legal Notice Drafter",
    title: "Start a notice drafting workflow",
    query: "Draft a legal notice checklist for money recovery under Indian law",
    body: `
      <label>Notice type
        <select id="tool-notice-type">
          <option>Money recovery</option>
          <option>Cheque dishonour under Section 138 NI Act</option>
          <option>Tenant eviction</option>
          <option>Consumer complaint</option>
        </select>
      </label>
      <label>Opponent or recipient
        <input id="tool-opponent" placeholder="Example: ABC Traders">
      </label>
      <button type="button" data-tool-action="notice-drafter">Send to AI Assistant</button>
      <div class="legal-tool-result" id="tool-result">This opens a structured drafting prompt in the LegalMitra AI box. Final notice must be reviewed by a professional before dispatch.</div>
    `,
  },
  limitation: {
    requiredPlan: "starter",
    label: "Limitation Calculator",
    title: "Indicative limitation deadline",
    query: "Calculate limitation period and filing deadline checklist under Indian law",
    body: `
      <label>Cause of action date
        <input id="tool-date" type="date">
      </label>
      <label>Matter type
        <select id="tool-limitation-type">
          <option value="3">Money recovery / specific performance orientation - 3 years</option>
          <option value="12">Possession of immovable property orientation - 12 years</option>
          <option value="1">Tort or damages orientation - 1 year</option>
        </select>
      </label>
      <button type="button" data-tool-action="limitation">Calculate date</button>
      <div class="legal-tool-result" id="tool-result">Select date and matter type. This is only an orientation tool; limitation depends on facts, statute, exclusions, condonation, and forum.</div>
    `,
  },
  "stamp-duty": {
    requiredPlan: "growth",
    label: "Stamp Duty Estimator",
    title: "Indicative property stamp duty estimate",
    query: "Explain stamp duty and registration charge checklist for an Indian property transaction",
    body: `
      <label>Property value in rupees
        <input id="tool-property-value" type="number" min="0" placeholder="Example: 10000000">
      </label>
      <label>Indicative rate
        <select id="tool-stamp-rate">
          <option value="5">5%</option>
          <option value="6">6%</option>
          <option value="7">7%</option>
        </select>
      </label>
      <button type="button" data-tool-action="stamp-duty">Estimate duty</button>
      <div class="legal-tool-result" id="tool-result">Enter property value for a broad estimate. Exact duty depends on state, city, property type, gender concessions, and registration rules.</div>
    `,
  },
  "hsn-search": {
    requiredPlan: "growth",
    label: "HSN Code Search",
    title: "HSN classification orientation",
    query: "Find HSN code search checklist and GST invoice classification risks",
    body: `
      <label>Product or service
        <input id="tool-hsn-query" placeholder="Example: laptop, software, legal services">
      </label>
      <button type="button" data-tool-action="hsn-search">Search indicative code</button>
      <div class="legal-tool-result" id="tool-result">Search a term to see indicative classification guidance. Verify classification against official GST notifications and product facts.</div>
    `,
  },
};

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(amount) || 0);
}

function sendToolQuery(prompt) {
  if (!queryInput) return;
  queryInput.value = prompt;
  document.getElementById("assistant")?.scrollIntoView({ behavior: "smooth", block: "start" });
  queryInput.focus();
}

function renderLegalTool(toolKey) {
  const tool = legalTools[toolKey];
  if (!tool || !legalToolPanel) return;
  if (!requirePlan(tool.requiredPlan || "starter", tool.label, `${tool.label} is not included in the ${PLAN_DETAILS[currentPlan].label} plan.`)) {
    return;
  }
  legalToolPanel.innerHTML = `
    <span>${escapeHtml(tool.label)}</span>
    <h3>${escapeHtml(tool.title)}</h3>
    <div class="legal-tool-form">${tool.body}</div>
    <button class="legal-tool-ai-button" type="button" data-tool-ai="${escapeHtml(toolKey)}">Open in LegalMitra AI</button>
  `;
  legalToolPanel.scrollIntoView({ behavior: "smooth", block: "center" });
}

function handleToolAction(action) {
  const result = document.getElementById("tool-result");
  if (!result) return;

  if (action === "court-fee") {
    const amount = Number(document.getElementById("tool-amount")?.value || 0);
    const state = document.getElementById("tool-state")?.selectedOptions?.[0]?.textContent || "selected jurisdiction";
    if (!amount) {
      result.textContent = "Enter the claim value first.";
      return;
    }
    const estimated = Math.max(200, Math.round(amount * 0.03));
    result.innerHTML = `<strong>Indicative estimate for ${escapeHtml(state)}:</strong> around ${formatCurrency(estimated)}. Verify exact slabs, maximum caps, valuation rules, and registry practice before filing.`;
    return;
  }

  if (action === "gst-finder") {
    const term = (document.getElementById("tool-gst-query")?.value || "").trim().toLowerCase();
    const known = term.includes("laptop")
      ? "Laptops are commonly mapped around HSN 8471 with 18% GST, subject to current notification verification."
      : term.includes("legal")
        ? "Legal services may involve reverse-charge treatment depending on recipient and service facts. Verify GST notifications and exemption entries."
        : term.includes("software")
          ? "Software classification depends on licence, SaaS/service model, and supply facts. Common rates require SAC/HSN verification."
          : "No fixed local match. Use AI handoff for a classification checklist and verify official GST rate notifications.";
    result.innerHTML = `<strong>Indicative result:</strong> ${escapeHtml(known)}`;
    return;
  }

  if (action === "notice-drafter") {
    const type = document.getElementById("tool-notice-type")?.value || "legal notice";
    const opponent = document.getElementById("tool-opponent")?.value || "the opposite party";
    sendToolQuery(`Prepare a professional ${type} legal notice checklist and draft outline against ${opponent} under Indian law`);
    return;
  }

  if (action === "limitation") {
    const dateValue = document.getElementById("tool-date")?.value;
    const years = Number(document.getElementById("tool-limitation-type")?.value || 0);
    if (!dateValue || !years) {
      result.textContent = "Select cause of action date and matter type first.";
      return;
    }
    const deadline = new Date(`${dateValue}T00:00:00`);
    deadline.setFullYear(deadline.getFullYear() + years);
    deadline.setDate(deadline.getDate() - 1);
    result.innerHTML = `<strong>Indicative last date:</strong> ${deadline.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}. Check exclusions, acknowledgements, condonation, special statute, and forum-specific rules.`;
    return;
  }

  if (action === "stamp-duty") {
    const value = Number(document.getElementById("tool-property-value")?.value || 0);
    const rate = Number(document.getElementById("tool-stamp-rate")?.value || 0);
    if (!value || !rate) {
      result.textContent = "Enter property value and rate first.";
      return;
    }
    result.innerHTML = `<strong>Indicative stamp duty:</strong> ${formatCurrency(value * rate / 100)} at ${rate}%. Verify state law, property category, surcharge, registration fee, and concessions.`;
    return;
  }

  if (action === "hsn-search") {
    const term = (document.getElementById("tool-hsn-query")?.value || "").trim().toLowerCase();
    const guidance = term.includes("laptop")
      ? "Indicative HSN: 8471 for automatic data processing machines. Verify specifications and current GST rate."
      : term.includes("software")
        ? "Software may need HSN/SAC analysis depending on goods/service character, licensing, and delivery model."
        : term.includes("legal")
          ? "Legal services are generally service classification questions rather than HSN goods classification."
          : "Use product composition, use, trade description, and GST notifications to narrow classification.";
    result.innerHTML = `<strong>Classification orientation:</strong> ${escapeHtml(guidance)}`;
  }
}

async function copyLastAnswer() {
  if (!lastAnswerText) {
    return;
  }
  await navigator.clipboard?.writeText(lastAnswerText);
}

function cleanSpeechText(value) {
  return String(value || "")
    .split(/\r?\n/)
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) return false;
      if (/^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)) return false;
      return true;
    })
    .join(". ")
    .replace(/\|/g, ". ")
    .replace(/#{1,6}\s*/g, "")
    .replace(/\*\*/g, "")
    .replace(/\*/g, "")
    .replace(/`/g, "")
    .replace(/\[(.*?)\]\((.*?)\)/g, "$1")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function stopAnswerAudio(message = "Reading stopped.") {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
  activeSpeech = null;
  updateAnswerButtonState("audio", false);
  setAnswerStatus(message);
}

function readAnswerAloud() {
  if (!("speechSynthesis" in window)) {
    setAnswerStatus("Read aloud is not supported in this browser.");
    return;
  }

  if (window.speechSynthesis.speaking || window.speechSynthesis.pending || activeSpeech) {
    stopAnswerAudio();
    return;
  }

  const speechText = cleanSpeechText(lastAnswerText);
  if (!speechText) {
    setAnswerStatus("No response text available to read.");
    return;
  }

  const utterance = new SpeechSynthesisUtterance(speechText);
  utterance.rate = 0.92;
  utterance.pitch = 1;
  utterance.onend = () => {
    activeSpeech = null;
    updateAnswerButtonState("audio", false);
    setAnswerStatus("Reading completed.");
  };
  utterance.onerror = () => {
    activeSpeech = null;
    updateAnswerButtonState("audio", false);
    setAnswerStatus("Reading stopped.");
  };

  activeSpeech = utterance;
  updateAnswerButtonState("audio", true);
  setAnswerStatus("Reading response aloud. Click the speaker again to stop.");
  window.speechSynthesis.cancel();
  window.setTimeout(() => window.speechSynthesis.speak(utterance), 60);
}

function downloadLastAnswer() {
  if (!lastAnswerText) {
    return;
  }
  const blob = new Blob([lastAnswerText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "legalmitra-response.txt";
  link.click();
  URL.revokeObjectURL(url);
}

function renderIcon(name) {
  const icons = {
    like: '<path d="M7 10v10"/><path d="M15 6.5 14 10h5.5l-1.2 8.1a2.2 2.2 0 0 1-2.2 1.9H8a1 1 0 0 1-1-1v-8.4a2 2 0 0 1 .6-1.4L12.5 4a1.3 1.3 0 0 1 2.2 1.2l-.2 1.3Z"/>',
    dislike: '<path d="M7 14V4"/><path d="M15 17.5 14 14h5.5l-1.2-8.1A2.2 2.2 0 0 0 16.1 4H8a1 1 0 0 0-1 1v8.4a2 2 0 0 0 .6 1.4L12.5 20a1.3 1.3 0 0 0 2.2-1.2l-.2-1.3Z"/>',
    regenerate: '<path d="M21 12a9 9 0 0 1-15.3 6.4"/><path d="M3 12A9 9 0 0 1 18.3 5.6"/><path d="M18 2v4h-4"/><path d="M6 22v-4h4"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V6a2 2 0 0 1 2-2h10"/>',
    audio: '<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
    share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4"/><path d="m15.4 6.5-6.8 4"/>',
    save: '<path d="M6 3h12v18l-6-4-6 4V3Z"/>',
    download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    delete: '<path d="M4 7h16"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M6 7l1 14h10l1-14"/><path d="M9 7V4h6v3"/>',
    attach: '<path d="m21 12-8.5 8.5a5 5 0 0 1-7-7L14 5a3 3 0 0 1 4.2 4.2L9.7 17.7a1 1 0 0 1-1.4-1.4L16 8.6"/>',
    tune: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="14" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
    mic: '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    send: '<path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 24 24">${icons[name] || ""}</svg>`;
}

function iconButton(action, icon, label) {
  const pressed = ["like", "dislike", "save"].includes(action) ? ' aria-pressed="false"' : "";
  return `<button type="button" data-answer-action="${action}" title="${label}" aria-label="${label}"${pressed}>${renderIcon(icon)}</button>`;
}

function renderLandingContent(payload) {
  if (!payload || typeof payload !== "object") {
    return;
  }

  if (solutionsList && Array.isArray(payload.solutions) && payload.solutions.length) {
    solutionsList.innerHTML = payload.solutions.slice(0, 4).map((item, index) => `
      <article>
        <span>${String(index + 1).padStart(2, "0")}</span>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.summary)}</p>
      </article>
    `).join("");
  }

  if (faqList && Array.isArray(payload.faq) && payload.faq.length) {
    faqList.innerHTML = payload.faq.map((item, index) => `
      <details ${index === 0 ? "open" : ""}>
        <summary>${escapeHtml(item.question)}</summary>
        <p>${escapeHtml(item.answer)}</p>
      </details>
    `).join("");
  }

  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node && value) {
      node.textContent = value;
    }
  };

  setText("about-title", payload.about?.title);
  setText("about-summary", payload.about?.summary);
  setText("contact-title", payload.contact?.title);
  setText("contact-summary", payload.contact?.summary);
  setText("contact-email", payload.contact?.email);
  setText("privacy-summary", payload.policy?.privacy);
  setText("terms-summary", payload.policy?.terms);
  setText("footer-summary", payload.footer?.summary);

  const footerLinks = document.getElementById("footer-links");
  if (footerLinks && Array.isArray(payload.footer?.links) && payload.footer.links.length) {
    footerLinks.innerHTML = payload.footer.links.map((item) => `
      <a href="${escapeHtml(item.href)}">${escapeHtml(item.label)}</a>
    `).join("");
  }
}

function renderLiveItems(target, items, emptyText) {
  if (!target) return;
  if (!Array.isArray(items) || !items.length) {
    target.innerHTML = `<p class="legal-live-empty">${escapeHtml(emptyText)}</p>`;
    return;
  }

  target.innerHTML = items.slice(0, 5).map((item) => {
    const title = String(item.title || "Legal update").trim();
    const meta = [item.court || item.source, item.date || item.year].filter(Boolean).join(" - ");
    const summary = String(item.summary || "Open LegalMitra AI to research this update with source checks.").trim();
    const query = String(item.query || title).trim();
    const href = item.url ? String(item.url) : `./login.html?return=${encodeURIComponent(`./chat.html?q=${encodeURIComponent(query)}`)}`;
    const targetAttr = item.url ? ' target="_blank" rel="noopener noreferrer"' : "";
    return `
      <a class="legal-live-item" href="${escapeHtml(href)}"${targetAttr}>
        <span>${escapeHtml(meta || "LegalMitra scan")}</span>
        <strong>${escapeHtml(title)}</strong>
        <small>${escapeHtml(summary)}</small>
      </a>
    `;
  }).join("");
}

async function loadLiveLegalIntelligence(kind = "all") {
  const tasks = [];
  if ((kind === "all" || kind === "cases") && majorCasesList) {
    majorCasesList.innerHTML = '<p class="legal-live-empty">Refreshing recent judgments...</p>';
    tasks.push(
      apiRequest(APP_KEY, "/api/v1/public-major-cases", { method: "GET", timeoutMs: 15000 }).then((result) => {
        renderLiveItems(
          majorCasesList,
          result.ok ? result.payload?.cases : [],
          result.ok ? "No recent judgments available right now." : `Could not load recent judgments: HTTP ${result.status}`,
        );
      })
    );
  }
  if ((kind === "all" || kind === "news") && legalNewsList) {
    legalNewsList.innerHTML = '<p class="legal-live-empty">Refreshing official legal updates...</p>';
    tasks.push(
      apiRequest(APP_KEY, "/api/v1/public-legal-news", { method: "GET", timeoutMs: 15000 }).then((result) => {
        renderLiveItems(
          legalNewsList,
          result.ok ? result.payload?.news : [],
          result.ok ? "No official legal updates available right now." : `Could not load legal updates: HTTP ${result.status}`,
        );
      })
    );
  }

  await Promise.allSettled(tasks);
}

function renderTemplateDetail(template) {
  if (!templateDetail || !template) return;
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
          ? `<ul>${fields.slice(0, 16).map((field) => `
              <li>
                <span>${escapeHtml(field.label || field.id)}</span>
                <small>${field.required ? "Required" : "Optional"} - ${escapeHtml(field.type || "text")}</small>
              </li>
            `).join("")}</ul>`
          : "<p>No field specification available for this template.</p>"
      }
    </div>
    <div class="legal-template-actions">
      <a href="./login.html?return=./chat.html">Sign in to generate draft</a>
      <button type="button" data-template-query="${escapeHtml(template.name || template.template_id)}">Ask AI about this template</button>
    </div>
  `;
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

  const first = ordered[0];
  if (first) {
    renderTemplateDetail(first);
  }
}

function formatHistoryDate(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) {
    return "Saved chat";
  }
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function renderPersonalHistory(items) {
  if (!historyList || !historyStatus) {
    return;
  }
  if (!items.length) {
    historyStatus.textContent = getAccessToken()
      ? "No saved LegalMitra chats yet. Your new questions will appear here."
      : "Sign in to load your personal chat history.";
    historyList.innerHTML = "";
    return;
  }
  historyStatus.textContent = `${items.length} personal chat(s). Only your own history is shown.`;
  historyList.innerHTML = items.map((item) => `
    <button type="button" data-history-id="${escapeHtml(item.record_id || "")}">
      <strong>${escapeHtml(item.query || "LegalMitra chat")}</strong>
      <span>${escapeHtml(formatHistoryDate(item.created_at))} - expires in ${escapeHtml(String(item.retention_days || ""))} days</span>
    </button>
  `).join("");
  historyList.querySelectorAll("[data-history-id]").forEach((button) => {
    const row = items.find((item) => item.record_id === button.getAttribute("data-history-id"));
    button.addEventListener("click", () => {
      if (!row) return;
      queryInput.value = row.query || "";
      renderLegalAnswer({
        ok: true,
        status: 200,
        payload: {
          response: row.response || "",
          provider: row.provider || "legalmitra_history",
          strategy: row.strategy || "saved_history",
          citations: row.citations || [],
          answer_id: row.record_id,
        },
      });
    });
  });
}

function renderPersonalUploads(items) {
  if (!uploadHistoryList || !uploadHistoryStatus) {
    return;
  }
  if (!items.length) {
    uploadHistoryStatus.textContent = getAccessToken()
      ? "No retained uploaded documents yet."
      : "Sign in to load your uploaded documents.";
    uploadHistoryList.innerHTML = "";
    return;
  }
  uploadHistoryStatus.textContent = `${items.length} personal upload(s). Only your own uploads are shown.`;
  uploadHistoryList.innerHTML = items.map((item) => `
    <button type="button" data-upload-id="${escapeHtml(item.upload_id || "")}">
      <strong>${escapeHtml(item.source_filename || "Uploaded document")}</strong>
      <span>${escapeHtml(formatHistoryDate(item.created_at))} - ${(Number(item.file_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB - retention ${escapeHtml(String(item.retention_days || ""))} days</span>
    </button>
  `).join("");
}

async function loadPersonalHistory() {
  if (!historyList || !historyStatus) {
    return;
  }
  if (!getAccessToken()) {
    renderPersonalHistory([]);
    renderPersonalUploads([]);
    return;
  }
  historyStatus.textContent = "Loading your personal chat history...";
  uploadHistoryStatus.textContent = "Loading your uploaded documents...";
  const result = await apiRequest(APP_KEY, "/api/v1/legalmitra/history?limit=50", { method: "GET" });
  const uploadsResult = await apiRequest(APP_KEY, "/api/v1/legalmitra/uploads?limit=50", { method: "GET" });
  if (!result.ok) {
    historyStatus.textContent = result.status === 401
      ? "Sign in to load your personal chat history."
      : "Could not load chat history.";
    historyList.innerHTML = "";
  } else {
    renderPersonalHistory(Array.isArray(result.payload?.items) ? result.payload.items : []);
  }

  if (!uploadsResult.ok) {
    uploadHistoryStatus.textContent = uploadsResult.status === 401
      ? "Sign in to load your uploaded documents."
      : "Could not load uploaded documents.";
    uploadHistoryList.innerHTML = "";
  } else {
    renderPersonalUploads(Array.isArray(uploadsResult.payload?.items) ? uploadsResult.payload.items : []);
  }
}

async function loadTemplateLibrary() {
  if (!templateList || !templateLibraryStatus) return;
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
      <p class="legal-template-empty">Check Backend API base URL and confirm the backend is running on http://127.0.0.1:8000.</p>
    `;
    renderJson(apiOutput, { templateStrategy: strategyResult, templates: templatesResult });
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

async function loadLandingContent() {
  const content = await apiRequest(APP_KEY, "/api/v1/legalmitra/landing-content", { method: "GET" });
  if (content.ok) {
    renderLandingContent(content.payload);
  }
}

async function updateUsageCounter() {
  if (!usageCounter || !getAccessToken()) {
    currentPlan = "starter";
    hasPrivilegedUsageAccess = false;
    if (usageCounter) {
      usageCounter.textContent = "0/10";
      usageCounter.title = "Starter plan: 5 daily AI research queries";
    }
    return;
  }

  const result = await apiRequest(APP_KEY, "/api/v1/users/me/usage", { method: "GET" });
  if (!result.ok) {
    return;
  }

  const used = result.payload?.usage?.daily_research?.count ?? 0;
  const limit = result.payload?.usage?.daily_research?.limit ?? 10;
  hasPrivilegedUsageAccess = Boolean(result.payload?.privileged_usage_access);
  currentPlan = hasPrivilegedUsageAccess
    ? "professional"
    : normalizePlan(result.payload?.effective_tier || result.payload?.tier);
  if (hasPrivilegedUsageAccess) {
    usageCounter.textContent = "Admin";
    usageCounter.title = "Platform owner/admin access: usage restrictions bypassed";
    return;
  }
  usageCounter.textContent = `${used}/${limit ?? "∞"}`;
  usageCounter.title = `${PLAN_DETAILS[currentPlan].label} research usage: ${used}/${limit ?? "unlimited"}`;
}

function renderLegalAnswer(result) {
  if (!answerPanel) {
    return;
  }

  if (activeSpeech && result) {
    stopAnswerAudio("");
  }

  if (!result) {
    lastAnswerMeta = null;
    answerPanel.innerHTML = '<div class="legal-answer-empty">Ask a question to see the LegalMitra response here.</div>';
    return;
  }

  if (result.status === 401) {
    answerPanel.innerHTML = `
      <div class="legal-answer-error">
        <strong>LegalMitra login required</strong>
        <span>Sign in to LegalMitra, then continue your legal research from the chat workspace.</span>
        <a class="button" href="./login.html?return=./chat.html">Open login page</a>
      </div>
    `;
    return;
  }

  const detail = String(result.payload?.detail || result.payload?.message || "");
  if (result.status === 403 && detail.includes("Legal Agreement Required")) {
    answerPanel.innerHTML = `
      <div class="legal-answer-error">
        <strong>Terms acceptance required</strong>
        <span>Sign in again from the LegalMitra login page so your legal terms acceptance can be refreshed.</span>
        <a class="button" href="./login.html?return=./chat.html">Open login page</a>
      </div>
    `;
    return;
  }

  if (result.status === 402) {
    showUpgradePrompt({
      feature: "More LegalMitra usage",
      requiredPlan: detail.toLowerCase().includes("official") ? "professional" : "growth",
      reason: detail || "You have reached the limit for your current plan.",
    });
    answerPanel.innerHTML = `
      <div class="legal-answer-error">
        <strong>Plan limit reached</strong>
        <span>${escapeHtml(detail || "Upgrade to continue using this feature.")}</span>
      </div>
    `;
    return;
  }

  if (!result.ok) {
    answerPanel.innerHTML = `
      <div class="legal-answer-error">
        <strong>LegalMitra could not complete this query</strong>
        <span>${escapeHtml(result.payload?.detail || result.payload?.message || "Check backend logs and try again.")}</span>
      </div>
    `;
    return;
  }

  const response = result.payload?.response || result.payload?.answer || "No response text returned.";
  lastAnswerText = String(response || "");
  const strategy = result.payload?.strategy || "legal-research";
  const provider = result.payload?.provider || (String(strategy).includes("claude") ? "claude_legal_counsel" : "legalmitra");
  const answerId = result.payload?.answer_id || result.payload?.response_id || hashText(`${queryInput.value}|${provider}|${strategy}|${lastAnswerText}`);
  lastAnswerMeta = {
    id: answerId,
    query: queryInput.value,
    provider,
    strategy,
  };
  const storedFeedback = loadAnswerFeedback()[answerId] || {};
  const citations = Array.isArray(result.payload?.citations) ? result.payload.citations : [];
  const followUps = buildFollowUps(queryInput.value, response);
  const citationHtml = citations.length
    ? `<div class="legal-answer-citations"><strong>Sources</strong>${citations.slice(0, 4).map((citation, index) => {
        const title = citation.title || citation.reference || citation.source || `Source ${index + 1}`;
        const snippet = citation.snippet || citation.text || "";
        return `<p><b>${escapeHtml(title)}</b>${snippet ? `<span>${escapeHtml(snippet)}</span>` : ""}</p>`;
      }).join("")}</div>`
    : "";

  answerPanel.innerHTML = `
    <div class="legal-answer-card">
      <div class="legal-answer-topline">
        <div class="legal-answer-meta">
          <span>${escapeHtml(provider)}</span>
          <span>${escapeHtml(strategy)}</span>
        </div>
        <div class="legal-answer-actions">
          ${iconButton("like", "like", "Mark helpful")}
          ${iconButton("dislike", "dislike", "Mark not helpful")}
          ${iconButton("regenerate", "regenerate", "Regenerate")}
          ${iconButton("copy", "copy", "Copy")}
          ${iconButton("audio", "audio", "Read aloud")}
          ${iconButton("share", "share", "Share")}
          ${iconButton("save", "save", "Save")}
          ${iconButton("download", "download", "Download")}
          ${iconButton("clear", "delete", "Clear")}
        </div>
      </div>
      <div class="legal-answer-status" id="answer-action-status" aria-live="polite"></div>
      <div class="legal-answer-body">${renderLegalMarkdown(response)}</div>
      ${citationHtml}
      <div class="legal-next-actions">
        <strong>Next actions</strong>
        <div>
          ${followUps.map((item) => `<button type="button" data-follow-up="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join("")}
        </div>
      </div>
    </div>
  `;
  updateAnswerButtonState("like", storedFeedback.kind === "rating" && storedFeedback.value === "helpful");
  updateAnswerButtonState("dislike", storedFeedback.kind === "rating" && storedFeedback.value === "not_helpful");
  updateAnswerButtonState("save", Boolean(storedFeedback.saved));
}

function renderModules(modules, options = {}) {
  const preview = options.preview !== false;
  nav.innerHTML = "";
  moduleList.innerHTML = "";

  modules.forEach((module) => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = module.enabled ? "" : "locked";
    link.setAttribute("aria-disabled", module.enabled ? "false" : "true");
    link.textContent = module.display_name;
    nav.appendChild(link);

    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${module.display_name}</strong>
      <span class="muted">${module.module_key} -> ${module.frontend_path || "no frontend path yet"}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : preview ? "preview only" : "locked"}</span>
    `;
    moduleList.appendChild(item);
  });
}

async function runChecks() {
  const health = await loadHealth(APP_KEY);
  if (healthPill) {
    healthPill.textContent = statusLabel(health);
    healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;
  }

  const modules = await loadModules(APP_KEY);
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (modules.ok) {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules(fallbackModules);
  }
}

async function askLegalMitra() {
  const query = String(queryInput.value || "legal update India").trim();
  const outputMode = String(outputModeInput.value || "advocate_research");
  const askButton = document.getElementById("ask-legalmitra");
  if (!IS_CHAT_PAGE) {
    if (getAccessToken()) {
      window.location.href = buildChatUrl({ auto: true });
    } else {
      redirectToLogin();
    }
    return;
  }
  if (!getAccessToken()) {
    setChatWorkspaceActive(false);
    renderLegalAnswer({
      ok: false,
      status: 401,
      payload: {
        detail: "Login required",
      },
    });
    redirectToLogin();
    return;
  }
  setChatWorkspaceActive(true);
  if (askButton) {
    askButton.disabled = true;
    askButton.textContent = "Asking...";
  }
  if (answerPanel) {
    answerPanel.innerHTML = '<div class="legal-answer-loading">LegalMitra is preparing a source-aware response...</div>';
  }
  const result = await apiRequest(APP_KEY, "/api/v1/legal-research", {
    method: "POST",
    timeoutMs: 90000,
    body: JSON.stringify({
      query,
      query_type: outputMode,
    }),
  });
  renderJson(apiOutput, result);
  renderLegalAnswer(result);
  updateUsageCounter();
  if (result.ok) {
    loadPersonalHistory();
  }
  if (askButton) {
    askButton.disabled = false;
    askButton.textContent = "Ask AI";
  }
}

async function askFollowUp() {
  const followUp = String(followUpInput.value || "").trim();
  if (!followUp) {
    return;
  }
  queryInput.value = followUp;
  await askLegalMitra();
  followUpInput.value = "";
}

async function loginLegalMitra() {
  const email = String(loginEmailInput.value || "").trim();
  const password = String(loginPasswordInput.value || "");
  const result = await apiRequest(APP_KEY, "/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  renderJson(apiOutput, result);
  if (!result.ok || !result.payload?.access_token) {
    renderLegalAnswer(result);
    return;
  }

  setAccessToken(result.payload.access_token);
  tokenInput.value = result.payload.access_token;
  setChatWorkspaceActive(true);
  await hydrateAuthHeader();
  const terms = await acceptLegalTerms();
  renderJson(apiOutput, { login: { ok: true, status: result.status }, terms });
  await runChecks();
  await updateUsageCounter();
  await loadPersonalHistory();
  renderLegalAnswer({
    ok: true,
    status: 200,
    payload: {
      provider: "local_session",
      strategy: "legalmitra_login_ready",
      response: "LegalMitra login is ready. Ask a legal question from the landing page query box.",
      citations: [],
    },
  });
}

async function acceptLegalTerms() {
  const result = await apiRequest(APP_KEY, "/api/v1/users/accept-terms", {
    method: "POST",
  });
  renderJson(apiOutput, result);
  return result;
}

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  runChecks();
  loadPersonalHistory();
});

document.getElementById("run-checks").addEventListener("click", runChecks);
document.getElementById("ask-legalmitra").addEventListener("click", askLegalMitra);
document.getElementById("ask-follow-up").addEventListener("click", askFollowUp);
document.getElementById("voice-input").innerHTML = renderIcon("mic");
document.getElementById("ask-follow-up").innerHTML = renderIcon("send");
document.querySelector(".legal-followup-tools button[aria-label='Attach document']").innerHTML = renderIcon("attach");
document.querySelector(".legal-followup-tools button[aria-label='Adjust response mode']").innerHTML = renderIcon("tune");
followUpInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    askFollowUp();
  }
});
document.getElementById("login-legalmitra").addEventListener("click", loginLegalMitra);
document.getElementById("accept-terms").addEventListener("click", acceptLegalTerms);
document.getElementById("clear-token").addEventListener("click", () => {
  clearAccessToken();
  tokenInput.value = "";
  setChatWorkspaceActive(false);
  renderSignedOutHeader();
  runChecks();
  loadPersonalHistory();
});

logoutButton?.addEventListener("click", () => {
  clearAccessToken();
  if (tokenInput) {
    tokenInput.value = "";
  }
  setChatWorkspaceActive(false);
  renderSignedOutHeader();
  renderPersonalHistory([]);
  renderPersonalUploads([]);
});

refreshHistoryButton?.addEventListener("click", loadPersonalHistory);

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    const toolKey = button.getAttribute("data-tool");
    if (toolKey) {
      renderLegalTool(toolKey);
      return;
    }
    queryInput.value = button.getAttribute("data-query") || queryInput.value;
    const mode = button.getAttribute("data-mode");
    if (mode && outputModeInput) {
      outputModeInput.value = mode;
    }
    queryInput.focus();
  });
});

legalToolPanel?.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-tool-action]");
  if (actionButton) {
    handleToolAction(actionButton.getAttribute("data-tool-action"));
    return;
  }
  const aiButton = event.target.closest("[data-tool-ai]");
  if (aiButton) {
    const tool = legalTools[aiButton.getAttribute("data-tool-ai")];
    sendToolQuery(tool?.query || queryInput?.value || "");
  }
});

document.querySelectorAll("[data-upgrade-plan]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const requiredPlan = normalizePlan(link.getAttribute("data-upgrade-plan"));
    showUpgradePrompt({
      feature: `${PLAN_DETAILS[requiredPlan].label} plan`,
      requiredPlan,
      reason: `You are currently on ${PLAN_DETAILS[currentPlan].label}. Upgrade when you are ready to enable ${PLAN_DETAILS[requiredPlan].limit}.`,
    });
  });
});

templateList?.addEventListener("click", async (event) => {
  const target = event.target instanceof HTMLElement ? event.target.closest("[data-template-id]") : null;
  if (!(target instanceof HTMLElement)) return;

  templateList.querySelectorAll("[data-template-id]").forEach((node) => node.classList.remove("active"));
  target.classList.add("active");

  const templateId = target.getAttribute("data-template-id");
  if (!templateId) return;
  const result = await apiRequest(APP_KEY, `/api/v1/v2/templates/${encodeURIComponent(templateId)}`, {
    method: "GET",
    timeoutMs: 10000,
  });
  if (result.ok) {
    renderTemplateDetail(result.payload);
  } else if (templateDetail) {
    templateDetail.innerHTML = `
      <span>Template load failed</span>
      <h3>HTTP ${result.status}</h3>
      <p>${escapeHtml(result.payload?.detail || "Could not load template detail from backend.")}</p>
    `;
  }
});

templateDetail?.addEventListener("click", (event) => {
  const target = event.target instanceof HTMLElement ? event.target.closest("[data-template-query]") : null;
  if (!(target instanceof HTMLElement)) return;
  queryInput.value = `Explain and help me prepare a ${target.getAttribute("data-template-query")} for Indian law use.`;
  outputModeInput.value = "drafting";
  queryInput.focus();
  window.location.hash = "assistant";
});

reloadTemplatesButton?.addEventListener("click", loadTemplateLibrary);
refreshMajorCasesButton?.addEventListener("click", () => loadLiveLegalIntelligence("cases"));
refreshLegalNewsButton?.addEventListener("click", () => loadLiveLegalIntelligence("news"));

document.getElementById("insights-list")?.addEventListener("click", (event) => {
  const target = event.target instanceof HTMLElement ? event.target.closest("[data-article-id]") : null;
  if (!(target instanceof HTMLElement)) return;
  window.location.href = `./article.html?id=${encodeURIComponent(target.getAttribute("data-article-id") || "")}`;
});

document.getElementById("insights-list")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const target = event.target instanceof HTMLElement ? event.target.closest("[data-article-id]") : null;
  if (!(target instanceof HTMLElement)) return;
  event.preventDefault();
  target.click();
});

answerPanel.addEventListener("click", async (event) => {
  const clicked = event.target;
  if (!(clicked instanceof Element)) {
    return;
  }

  const target = clicked.closest("[data-answer-action]");
  const action = target instanceof HTMLElement ? target.getAttribute("data-answer-action") : null;
  if (["share", "save", "download"].includes(action || "")
    && !requirePlan("growth", target?.getAttribute("aria-label") || "Premium response action", "Starter can read, copy, rate, and ask limited questions. Saving, sharing, and downloading response workspaces require Growth or Professional.")) {
    return;
  }
  if (action === "copy") {
    await copyLastAnswer();
    target.classList.add("active");
    setAnswerStatus("Response copied to clipboard.");
    window.setTimeout(() => updateAnswerButtonState("copy", false), 1200);
  } else if (action === "download") {
    downloadLastAnswer();
    target.classList.add("active");
    setAnswerStatus("Response downloaded as text.");
    window.setTimeout(() => updateAnswerButtonState("download", false), 1200);
  } else if (action === "regenerate") {
    target.classList.add("active");
    setAnswerStatus("Regenerating response...");
    askLegalMitra();
  } else if (action === "audio") {
    readAnswerAloud();
  } else if (action === "share") {
    updateAnswerButtonState("share", true);
    try {
      if (navigator.share && lastAnswerText) {
        await navigator.share({ title: "LegalMitra response", text: lastAnswerText });
        setAnswerStatus("Share sheet opened.");
      } else {
        await copyLastAnswer();
        setAnswerStatus("Sharing is not available in this browser. Response copied instead.");
      }
    } catch {
      await copyLastAnswer();
      setAnswerStatus("Share was cancelled or blocked. Response copied instead.");
    }
    window.setTimeout(() => updateAnswerButtonState("share", false), 1200);
  } else if (action === "like") {
    updateAnswerButtonState("like", true);
    updateAnswerButtonState("dislike", false);
    await persistAnswerFeedback("rating", "helpful");
    setAnswerStatus("Feedback saved: helpful. This will be used to improve LegalMitra responses.");
  } else if (action === "dislike") {
    updateAnswerButtonState("dislike", true);
    updateAnswerButtonState("like", false);
    await persistAnswerFeedback("rating", "not_helpful");
    setAnswerStatus("Feedback saved: not helpful. This will be used to improve LegalMitra responses.");
  } else if (action === "save") {
    const isSaved = target.getAttribute("aria-pressed") !== "true";
    updateAnswerButtonState("save", isSaved);
    if (lastAnswerMeta?.id) {
      const feedback = loadAnswerFeedback();
      feedback[lastAnswerMeta.id] = {
        ...(feedback[lastAnswerMeta.id] || {}),
        id: lastAnswerMeta.id,
        saved: isSaved,
        query: lastAnswerMeta.query,
        provider: lastAnswerMeta.provider,
        strategy: lastAnswerMeta.strategy,
        timestamp: new Date().toISOString(),
      };
      saveAnswerFeedback(feedback);
    }
    setAnswerStatus(isSaved ? "Response saved locally." : "Response removed from saved items.");
  } else if (action === "print") {
    window.print();
  } else if (action === "clear") {
    lastAnswerText = "";
    lastAnswerMeta = null;
    stopAnswerAudio("");
    renderLegalAnswer(null);
  }

  const followUpTarget = clicked.closest("[data-follow-up]");
  const followUp = followUpTarget instanceof HTMLElement ? followUpTarget.getAttribute("data-follow-up") : null;
  if (followUp) {
    followUpInput.value = followUp;
    followUpInput.focus();
  }
});

apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
loginEmailInput.value = "superadmin@sanmitra.local";
hydrateAuthHeader();
const chatParams = new URLSearchParams(window.location.search);
if (IS_CHAT_PAGE) {
  const initialQuery = String(chatParams.get("q") || "").trim();
  const initialMode = String(chatParams.get("mode") || "").trim();
  const handoffType = String(chatParams.get("handoff") || "").trim();
  let handoffQuery = "";
  let handoffMode = "";
  if (handoffType === "template") {
    try {
      const rawHandoff = sessionStorage.getItem(TEMPLATE_CHAT_HANDOFF_KEY)
        || localStorage.getItem(TEMPLATE_CHAT_HANDOFF_KEY)
        || "{}";
      const handoff = JSON.parse(rawHandoff);
      handoffQuery = String(handoff.query || "").trim();
      handoffMode = String(handoff.mode || "").trim();
      sessionStorage.removeItem(TEMPLATE_CHAT_HANDOFF_KEY);
      localStorage.removeItem(TEMPLATE_CHAT_HANDOFF_KEY);
    } catch {
      handoffQuery = "";
      handoffMode = "";
    }
  }
  if ((handoffQuery || initialQuery) && queryInput) {
    queryInput.value = handoffQuery || initialQuery;
  }
  if ((handoffMode || initialMode) && outputModeInput) {
    outputModeInput.value = handoffMode || initialMode;
  }
  if (!getAccessToken()) {
    redirectToLogin();
  } else {
    setChatWorkspaceActive(true);
  }
}
renderModules(fallbackModules);
renderModuleState(moduleState);
runChecks();
updateUsageCounter();
loadPersonalHistory();
loadLandingContent();
loadLiveLegalIntelligence();
loadTemplateLibrary();
if (IS_CHAT_PAGE && chatParams.get("auto") === "1" && getAccessToken()) {
  askLegalMitra();
}
