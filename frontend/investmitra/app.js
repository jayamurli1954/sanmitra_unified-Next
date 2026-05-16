import {
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

const APP_KEY = "investmitra";

const fallbackModules = [
  { module_key: "investment", display_name: "InvestMitra Portfolio", frontend_path: "/investment", nav_group: "Portfolio", enabled: true },
  { module_key: "portfolio", display_name: "Portfolio Analytics", frontend_path: "/investment/portfolio", nav_group: "Portfolio", enabled: true },
  { module_key: "investment_research", display_name: "InvestMitra Research Integrations", frontend_path: "/investment/research", nav_group: "Research", enabled: false },
  { module_key: "broker_research", display_name: "Read-Only Broker Research Context", frontend_path: "/investment/broker-research", nav_group: "Research", enabled: false },
  { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
];

const nav = document.getElementById("nav");
const moduleList = document.getElementById("module-list");
const apiOutput = document.getElementById("api-output");
const healthPill = document.getElementById("health-pill");
const moduleState = document.getElementById("module-state");
const apiBaseInput = document.getElementById("api-base");
const tokenInput = document.getElementById("access-token");

function renderModules(modules, options = {}) {
  const preview = options.preview !== false;
  nav.innerHTML = "";
  moduleList.innerHTML = "";

  modules.forEach((module) => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = module.enabled ? "" : "locked";
    link.setAttribute("aria-disabled", module.enabled ? "false" : "true");
    link.textContent = `${module.nav_group || "Module"}: ${module.display_name}`;
    nav.appendChild(link);

    const item = document.createElement("li");
    const safety = module.module_key === "broker_research" ? "read-only; no order tools" : module.module_key;
    item.innerHTML = `
      <strong>${module.display_name}</strong>
      <span class="muted">${safety} -> ${module.frontend_path || "no frontend path yet"}</span>
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

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  runChecks();
});

document.getElementById("run-checks").addEventListener("click", runChecks);
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
