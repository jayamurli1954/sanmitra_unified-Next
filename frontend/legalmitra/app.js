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
const queryInput = document.getElementById("query");

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
  healthPill.textContent = statusLabel(health);
  healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;

  const modules = await loadModules(APP_KEY);
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (modules.ok) {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules(fallbackModules);
  }
}

async function probeNews() {
  const query = encodeURIComponent(queryInput.value || "legal update India");
  const result = await apiRequest(APP_KEY, `/api/v1/legal/news?query=${query}&max_results=3`, { method: "GET" });
  renderJson(apiOutput, result);
}

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  runChecks();
});

document.getElementById("run-checks").addEventListener("click", runChecks);
document.getElementById("probe-news").addEventListener("click", probeNews);
document.getElementById("clear-token").addEventListener("click", () => {
  clearAccessToken();
  tokenInput.value = "";
  runChecks();
});

apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
renderModules(fallbackModules);
renderModuleState(moduleState);
runChecks();
