import {
  clearAccessToken,
  getAccessToken,
  getConfiguredApiBaseUrl,
  loadHealth,
  loadModules,
  renderJson,
  setAccessToken,
  setConfiguredApiBaseUrl,
  statusLabel,
} from "../shared/api-client.js";

const APP_KEY = "mitrabooks";

const experienceConfig = {
  mitrabooks: {
    title: "MitraBooks ERP",
    subtitle: "Unified shell for accounting-heavy SanMitra modules",
    logo: "../assets/brand/mitrabooks-logo.jpg",
    video: "../assets/brand/mitrabooks-logo.mp4",
    theme: "",
    scopeTitle: "MitraBooks Business Workspace",
    scopeCopy: "Business, GST, inventory, parties, vouchers, and financial reports stay close to the old MitraBooks accounting layout.",
    legacyTitle: "MitraBooks workspace",
    legacyCopy: "Business, GST, inventory, parties, vouchers, and financial reports.",
    modules: [
      { module_key: "business", display_name: "Dashboard", frontend_path: "/business", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounts", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "gst", display_name: "GST Compliance", frontend_path: "/gst", nav_group: "Compliance", enabled: true },
      { module_key: "inventory", display_name: "Inventory", frontend_path: "/inventory", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
    ],
  },
  mandir: {
    title: "MandirMitra",
    subtitle: "Temple, trust, donation, seva, and accounting workflows",
    logo: "../assets/brand/mandirmitra-logo.jpeg",
    video: "../assets/brand/mandirmitra-logo.mp4",
    theme: "mandir-theme",
    scopeTitle: "MandirMitra Temple Workspace",
    scopeCopy: "Preserves the old temple layout pattern: dashboard, donations, devotees, sevas, panchang, reports, and accounting.",
    legacyTitle: "MandirMitra layout mode",
    legacyCopy: "Saffron/green visual treatment and temple-first navigation are retained for user familiarity.",
    modules: [
      { module_key: "temple", display_name: "Dashboard", frontend_path: "/temple/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Donations", frontend_path: "/temple/donations", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Devotees", frontend_path: "/temple/devotees", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Sevas", frontend_path: "/temple/sevas", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Panchang", frontend_path: "/temple/panchang", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Reports", frontend_path: "/temple/reports", nav_group: "Administration", enabled: true },
    ],
  },
  gruha: {
    title: "GruhaMitra",
    subtitle: "Housing society operations with shared MitraBooks accounting",
    logo: "../assets/brand/gruhamitra-logo.png",
    video: "../assets/brand/gruhamitra-logo.mp4",
    theme: "gruha-theme",
    scopeTitle: "GruhaMitra Housing Workspace",
    scopeCopy: "Preserves the old housing layout pattern: dashboard, maintenance, members, complaints, reports, assets, and settings.",
    legacyTitle: "GruhaMitra layout mode",
    legacyCopy: "Housing-first navigation mirrors the old web app while using the unified shell.",
    modules: [
      { module_key: "housing", display_name: "Dashboard", frontend_path: "/housing/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Maintenance", frontend_path: "/housing/maintenance", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Members", frontend_path: "/housing/members", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Complaints", frontend_path: "/housing/complaints", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "housing", display_name: "Reports", frontend_path: "/housing/reports", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Settings", frontend_path: "/housing/settings", nav_group: "Administration", enabled: true },
    ],
  },
};

let currentExperience = "mitrabooks";

const appRoot = document.getElementById("app-root");
const brandLogo = document.getElementById("brand-logo");
const brandTitle = document.getElementById("brand-title");
const brandSubtitle = document.getElementById("brand-subtitle");
const scopeTitle = document.getElementById("scope-title");
const scopeCopy = document.getElementById("scope-copy");
const legacyTitle = document.getElementById("legacy-title");
const legacyCopy = document.getElementById("legacy-copy");
const legacyVideo = document.getElementById("legacy-video");
const legacyImage = document.getElementById("legacy-image");
const nav = document.getElementById("nav");
const moduleList = document.getElementById("module-list");
const apiOutput = document.getElementById("api-output");
const healthPill = document.getElementById("health-pill");
const apiBaseInput = document.getElementById("api-base");
const tokenInput = document.getElementById("access-token");

function renderModules(modules = experienceConfig[currentExperience].modules) {
  const config = experienceConfig[currentExperience];
  appRoot.className = `app ${config.theme}`.trim();
  brandLogo.src = config.logo;
  brandLogo.alt = config.title;
  brandTitle.textContent = config.title;
  brandSubtitle.textContent = config.subtitle;
  scopeTitle.textContent = config.scopeTitle;
  scopeCopy.textContent = config.scopeCopy;
  legacyTitle.textContent = config.legacyTitle;
  legacyCopy.textContent = config.legacyCopy;
  legacyImage.src = config.logo;
  legacyImage.alt = config.title;
  if (config.video && getAccessToken()) {
    legacyVideo.src = config.video;
    legacyVideo.hidden = false;
    legacyImage.hidden = true;
    legacyVideo.play().catch(() => {});
  } else {
    legacyVideo.pause();
    legacyVideo.removeAttribute("src");
    legacyVideo.load();
    legacyVideo.hidden = true;
    legacyImage.hidden = false;
  }

  nav.innerHTML = "";
  moduleList.innerHTML = "";

  modules.forEach((module) => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = module.enabled ? "" : "locked";
    link.textContent = `${module.nav_group || "Module"}: ${module.display_name}`;
    nav.appendChild(link);

    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${module.display_name}</strong>
      <span class="muted">${module.module_key} -> ${module.frontend_path || "no frontend path yet"}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : "available or planned"}</span>
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

  if (modules.ok && modules.payload.enabled_modules && currentExperience === "mitrabooks") {
    renderModules([...(modules.payload.enabled_modules || []), ...(modules.payload.available_modules || [])]);
  } else {
    renderModules();
  }
}

function setExperience(nextExperience) {
  currentExperience = nextExperience;
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${nextExperience === "mandir" ? "mandir" : nextExperience === "gruha" ? "gruha" : "mitrabooks"}`).classList.add("active");
  renderModules();
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
document.getElementById("mode-mitrabooks").addEventListener("click", () => setExperience("mitrabooks"));
document.getElementById("mode-mandir").addEventListener("click", () => setExperience("mandir"));
document.getElementById("mode-gruha").addEventListener("click", () => setExperience("gruha"));

apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
renderModules();
runChecks();
