// ====================================================================
// SECTION: SHELL BOOT — runChecks + platform dashboard + setExperience
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initShellBoot(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let healthPill;
let apiOutput;
let moduleState;
let dashboardPreview;

export function initShellBoot(injected) {
  deps = injected;
  healthPill = injected.healthPill;
  apiOutput = injected.apiOutput;
  moduleState = injected.moduleState;
  dashboardPreview = injected.dashboardPreview;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initShellBoot() must be called before using shell boot helpers");
  }
  return deps;
}

function getAccessToken(...args) { return requireDeps().getAccessToken(...args); }
function clearAllTokens(...args) { return requireDeps().clearAllTokens(...args); }
function loadHealth(...args) { return requireDeps().loadHealth(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }
function statusLabel(...args) { return requireDeps().statusLabel(...args); }
function moduleItemsFromPayload(...args) { return requireDeps().moduleItemsFromPayload(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function renderModuleState(...args) { return requireDeps().renderModuleState(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function updateSessionUi(...args) { return requireDeps().updateSessionUi(...args); }
function renderModules(...args) { return requireDeps().renderModules(...args); }
function setLoginStatus(...args) { return requireDeps().setLoginStatus(...args); }
function isPasswordRecoveryPanelOpen(...args) { return requireDeps().isPasswordRecoveryPanelOpen(...args); }
function isPlatformOwnerContext(...args) { return requireDeps().isPlatformOwnerContext(...args); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderPlatformDashboard(...args) { return requireDeps().renderPlatformDashboard(...args); }
function syncPlatformNavActiveState(...args) { return requireDeps().syncPlatformNavActiveState(...args); }
function loadMandirDashboard(...args) { return requireDeps().loadMandirDashboard(...args); }
function loadGruhaDashboard(...args) { return requireDeps().loadGruhaDashboard(...args); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessPartiesForHealth(...args) { return requireDeps().loadBusinessPartiesForHealth(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function refreshBooksHealthWidget(...args) { return requireDeps().refreshBooksHealthWidget(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function emptyPlatformDashboardPayload(...args) { return requireDeps().emptyPlatformDashboardPayload(...args); }
function loadAndRenderGroupedNav(...args) { return requireDeps().loadAndRenderGroupedNav(...args); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function setCurrentExperience(value) { requireDeps().setCurrentExperience(value); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getLastPlatformOwnerDashboard() { return requireDeps().getLastPlatformOwnerDashboard(); }
function setLastPlatformOwnerDashboard(value) { requireDeps().setLastPlatformOwnerDashboard(value); }
function getActivePlatformWorkspace() { return requireDeps().getActivePlatformWorkspace(); }
function setActivePlatformWorkspace(value) { requireDeps().setActivePlatformWorkspace(value); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function getAppKey() { return requireDeps().getAppKey(); }

export async function runChecks() {
  const activeAppKey = getExperienceAppKeys()[getCurrentExperience()] || getAppKey();
  const tokenAtStart = getAccessToken();
  const health = await loadHealth(activeAppKey);
  healthPill.textContent = statusLabel(health);
  healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;

  const modules = await loadModules(activeAppKey);
  if (modules.ok) {
    setLastModuleContext(modules.payload);
    updateTrustedContextUi(getLastModuleContext());
    updateSessionUi();
  }
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (!modules.ok && modules.status === 401) {
    // Ignore stale unauthenticated 401s that finish after a concurrent login.
    if (getAccessToken() && getAccessToken() !== tokenAtStart) {
      return;
    }
    setLastModuleContext(null);
    clearAllTokens();
    renderModules();
    if (!isPasswordRecoveryPanelOpen()) {
      setLoginStatus("warn", "Sign in required", "Enter your email and password to load tenant data.");
    }
    updateSessionUi();
    return;
  }

  if (!modules.ok && getCurrentExperience() === "mitrabooks") {
    setLastModuleContext(null);
    // Treat network/timeout failures the same as 401 when a cached token cannot
    // establish tenant context, so hosted smoke does not keep a dead session.
    if (tokenAtStart && getAccessToken() === tokenAtStart) {
      clearAllTokens();
      renderModules();
      if (!isPasswordRecoveryPanelOpen()) {
        setLoginStatus("warn", "Sign in required", "Enter your email and password to load tenant data.");
      }
      updateSessionUi();
      return;
    }
    renderModules();
    if (!isPasswordRecoveryPanelOpen()) {
      setLoginStatus("warn", "Tenant session required", "Sign in to load your MitraBooks dashboard.");
    }
    updateSessionUi();
    return;
  }

  if (modules.ok && getCurrentExperience() === "mitrabooks" && isPlatformOwnerContext(modules.payload)) {
    setCurrentExperience("platform");
    document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
    document.getElementById("mode-platform")?.classList.add("active");
    renderModules();
    setLoginStatus("ok", "Platform owner signed in", "Showing the platform-owner workspace. Business tenant data remains tenant-scoped.");
    updateSessionUi();
    await loadPlatformOwnerDashboard();
    return;
  }

  if (modules.ok && getCurrentExperience() === "mitrabooks") {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules();
  }

  if (getCurrentExperience() === "platform") {
    await loadPlatformOwnerDashboard();
  } else if (getCurrentExperience() === "mandir") {
    await loadMandirDashboard();
  } else if (getCurrentExperience() === "gruha") {
    await loadGruhaDashboard();
  } else if (getCurrentExperience() === "mitrabooks") {
    await loadBusinessAccounts();
    await loadBusinessPartiesForHealth();
    const accountingDrilldown = await loadAccountingDrilldownResult();
    renderJson(apiOutput, { health, modules, accounting_drilldown: accountingDrilldown });
    refreshBooksHealthWidget();
    dashboardPreview.innerHTML = renderDashboardPreview(getExperienceConfig()[getCurrentExperience()]);
  }
}

export async function loadPlatformOwnerDashboard() {
  const result = await apiRequest(getAppKey(), "/api/v1/platform-owner/dashboard", { method: "GET" });
  renderJson(apiOutput, { platform_owner_dashboard: result });
  if (result.ok) {
    setLastPlatformOwnerDashboard(result.payload);
    dashboardPreview.innerHTML = renderPlatformDashboard(result.payload);
    syncPlatformNavActiveState();
    return;
  }

  dashboardPreview.insertAdjacentHTML(
    "afterbegin",
    `<div class="module-state warn"><strong>Platform dashboard unavailable</strong><span>Provide a super-admin access token and run checks to load live platform-owner data.</span></div>`
  );
}

export function setExperience(nextExperience) {
  setCurrentExperience(nextExperience);
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${nextExperience}`)?.classList.add("active");
  if (nextExperience === "platform") {
    setActivePlatformWorkspace("dashboard");
  }
  renderModules();
  if (nextExperience === "platform") {
    loadPlatformOwnerDashboard();
  } else if (nextExperience === "mandir") {
    loadMandirDashboard();
  } else if (nextExperience === "gruha") {
    loadGruhaDashboard();
  } else if (nextExperience === "mitrabooks") {
    const appKey = getExperienceAppKeys()[nextExperience] || getAppKey();
    loadAndRenderGroupedNav(appKey);
    loadAccountingDrilldownResult().then(() => {
      dashboardPreview.innerHTML = renderDashboardPreview(getExperienceConfig()[getCurrentExperience()]);
    });
  }
}

