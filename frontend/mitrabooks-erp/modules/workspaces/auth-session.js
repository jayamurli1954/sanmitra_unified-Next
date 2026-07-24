// ====================================================================
// SECTION: AUTH + SESSION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAuthSession(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

let pendingForcedPasswordChange = false;

/** DOM refs bound once during init. */
let appRoot;
let sessionPill;
let topbarUser;
let topbarAvatar;
let sidebarAvatar;
let sidebarUserName;
let sidebarUserRole;
let loginEmail;
let loginPassword;
let tokenInput;
let accountMenuPanel;
let accountMenuTrigger;
let passwordForm;
let passwordStatus;
let passwordDialog;
let currentPasswordInput;
let newPasswordInput;
let confirmNewPasswordInput;
let currentOrgType;
let currentOrgTenant;
let dashboardPreview;
let apiOutput;
let moduleState;
let forgotPasswordForm;
let forgotPasswordEmail;
let resetPasswordForm;
let resetNewPasswordInput;
let resetConfirmPasswordInput;

export function initAuthSession(injected) {
  deps = injected;
  appRoot = injected.appRoot;
  sessionPill = injected.sessionPill;
  topbarUser = injected.topbarUser;
  topbarAvatar = injected.topbarAvatar;
  sidebarAvatar = injected.sidebarAvatar;
  sidebarUserName = injected.sidebarUserName;
  sidebarUserRole = injected.sidebarUserRole;
  loginEmail = injected.loginEmail;
  loginPassword = injected.loginPassword;
  tokenInput = injected.tokenInput;
  accountMenuPanel = injected.accountMenuPanel;
  accountMenuTrigger = injected.accountMenuTrigger;
  passwordForm = injected.passwordForm;
  passwordStatus = injected.passwordStatus;
  passwordDialog = injected.passwordDialog;
  currentPasswordInput = injected.currentPasswordInput;
  newPasswordInput = injected.newPasswordInput;
  confirmNewPasswordInput = injected.confirmNewPasswordInput;
  currentOrgType = injected.currentOrgType;
  currentOrgTenant = injected.currentOrgTenant;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
  moduleState = injected.moduleState;
  forgotPasswordForm = injected.forgotPasswordForm;
  forgotPasswordEmail = injected.forgotPasswordEmail;
  resetPasswordForm = injected.resetPasswordForm;
  resetNewPasswordInput = injected.resetNewPasswordInput;
  resetConfirmPasswordInput = injected.resetConfirmPasswordInput;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAuthSession() must be called before using auth-session helpers");
  }
  return deps;
}

function getAccessToken() { return requireDeps().getAccessToken(); }
function getRefreshToken() { return requireDeps().getRefreshToken(); }
function clearAllTokens() { return requireDeps().clearAllTokens(); }
function clearAccessToken() { return requireDeps().clearAccessToken(); }
function setAccessToken(value) { return requireDeps().setAccessToken(value); }
function setRefreshToken(value) { return requireDeps().setRefreshToken(value); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function setCurrentExperience(value) { requireDeps().setCurrentExperience(value); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getSelectedOrgType() { return requireDeps().getSelectedOrgType(); }
function getOrgSelectorMeta() { return requireDeps().getOrgSelectorMeta(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function getAppKey() { return requireDeps().getAppKey(); }
function getLoginEmailStorageKey() { return requireDeps().getLoginEmailStorageKey(); }
function getDefaultMitraBooksLoginEmail() { return requireDeps().getDefaultMitraBooksLoginEmail(); }
function getLoginRequestTimeoutMs() { return requireDeps().getLoginRequestTimeoutMs(); }
function getPendingPasswordResetToken() { return requireDeps().getPendingPasswordResetToken(); }
function setPendingPasswordResetToken(value) { requireDeps().setPendingPasswordResetToken(value); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function setLoginStatus(...args) { return requireDeps().setLoginStatus(...args); }
function statusDetailText(...args) { return requireDeps().statusDetailText(...args); }
function escapeHtml(...args) { return requireDeps().escapeHtml(...args); }
function setLastBusinessAccounts(...args) { return requireDeps().setLastBusinessAccounts(...args); }
function setLastBusinessParties(...args) { return requireDeps().setLastBusinessParties(...args); }
function clearVoucherListState(...args) { return requireDeps().clearVoucherListState(...args); }
function setLastAccountingDrilldown(...args) { return requireDeps().setLastAccountingDrilldown(...args); }
function renderModules(...args) { return requireDeps().renderModules(...args); }
function renderModuleState(...args) { return requireDeps().renderModuleState(...args); }
function initialExperience(...args) { return requireDeps().initialExperience(...args); }
function mandirPublicPaymentPageUrl(...args) { return requireDeps().mandirPublicPaymentPageUrl(...args); }
function loadAndRenderGroupedNav(...args) { return requireDeps().loadAndRenderGroupedNav(...args); }
function showMandirSplash(...args) { return requireDeps().showMandirSplash(...args); }
function hideMandirSplash(...args) { return requireDeps().hideMandirSplash(...args); }
function runChecks(...args) { return requireDeps().runChecks(...args); }
function delay(...args) { return requireDeps().delay(...args); }

export function hasTrustedSession() {
  if (!getAccessToken()) {
    return false;
  }
  if (getCurrentExperience() !== "mitrabooks") {
    return true;
  }
  return Boolean(getLastModuleContext() && typeof getLastModuleContext() === "object");
}

export function updateSessionUi() {
  const signedIn = hasTrustedSession();
  appRoot.classList.toggle("signed-in", signedIn);
  appRoot.classList.toggle("signed-out", !signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-in", signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-out", !signedIn);
  if (sessionPill) {
    sessionPill.textContent = signedIn ? "Signed in" : "Not signed in";
    sessionPill.className = `pill ${signedIn ? "ok" : "warn"}`;
  }
  const savedEmail = window.localStorage.getItem(getLoginEmailStorageKey()) || "";
  if (topbarUser) {
    topbarUser.textContent = compactAccountLabel(savedEmail || "Signed in");
    topbarUser.title = savedEmail || "Signed in";
  }
  if (topbarAvatar) {
    topbarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarAvatar) {
    sidebarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarUserName) {
    sidebarUserName.textContent = signedIn ? (savedEmail || "Signed in") : "Not signed in";
  }
  if (sidebarUserRole) {
    const role = getLastModuleContext()?.role || getLastModuleContext()?.user_role || "";
    sidebarUserRole.textContent = signedIn ? (role || "Tenant context pending") : "Sign in to load tenant";
  }

  // Update user credentials display in topbar
  const emailDisplay = document.getElementById("topbar-email-display");
  const menuEmailDisplay = document.getElementById("menu-email-display");
  const menuTenantDisplay = document.getElementById("menu-tenant-display");
  if (emailDisplay) {
    emailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuEmailDisplay) {
    menuEmailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuTenantDisplay && getLastModuleContext()?.tenant_id) {
    menuTenantDisplay.textContent = getLastModuleContext().tenant_id;
  }

  document.getElementById("topbar-actions")?.toggleAttribute("hidden", !signedIn);
  document.getElementById("sidebar-logout")?.toggleAttribute("hidden", !signedIn);
  if (loginEmail && !loginEmail.value) {
    loginEmail.value = savedEmail || getDefaultMitraBooksLoginEmail();
  }
  if (tokenInput) {
    tokenInput.value = getAccessToken();
  }
  const publicLink = document.getElementById("mandir-public-link");
  if (publicLink) {
    publicLink.href = mandirPublicPaymentPageUrl();
  }
}

export function compactAccountLabel(email) {
  const value = String(email || "").trim();
  if (!value.includes("@")) {
    return value || "Account";
  }
  const [name, domain] = value.split("@");
  const shortName = name.length > 12 ? `${name.slice(0, 10)}...` : name;
  const shortDomain = String(domain || "").split(".")[0] || domain;
  return `${shortName}@${shortDomain}`;
}

export function signOutAndReturnToLogin() {
  const rt = getRefreshToken();
  if (rt) {
    const appKey = getExperienceAppKeys()[getCurrentExperience()] || getAppKey();
    apiRequest(appKey, "/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: rt }),
    }).catch(() => {});
  }
  clearAllTokens();
  setLastModuleContext(null);
  setLastBusinessAccounts([]);
  setLastBusinessParties([]);
  clearVoucherListState();
  setLastAccountingDrilldown(null);
  if (tokenInput) {
    tokenInput.value = "";
  }
  if (loginPassword) {
    loginPassword.value = "";
  }
  setAuthPanelMode("login");
  setLoginStatus("", "", "");
  dashboardPreview.innerHTML = "";
  renderJson(apiOutput, {});
  renderModuleState(moduleState);
  setCurrentExperience(initialExperience());
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${getCurrentExperience()}`)?.classList.add("active");
  renderModules();
  updateSessionUi();
}

export function closeAccountMenu() {
  if (accountMenuPanel) {
    accountMenuPanel.hidden = true;
  }
  accountMenuTrigger?.setAttribute("aria-expanded", "false");
}

export function openPasswordDialog() {
  closeAccountMenu();
  passwordForm?.reset();
  _clearPasswordError();
  if (passwordStatus && pendingForcedPasswordChange) {
    const field = document.getElementById("password-error-field");
    if (field) field.style.display = "block";
    passwordStatus.className = "module-state warn";
    passwordStatus.innerHTML = "<strong>Temporary password in use</strong><span>Change the temporary password before opening the MitraBooks workspace.</span>";
  }
  passwordDialog?.showModal();
}

export async function loadCurrentUserProfile(appKey) {
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const result = await apiRequest(appKey, "/api/v1/users/me", {
    method: "GET",
    timeoutMs: getLoginRequestTimeoutMs(),
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return result.ok ? (result.payload || null) : null;
}

export async function completeWorkspaceSignIn(appKey) {
  if (getCurrentExperience() === "mitrabooks") {
    loadAndRenderGroupedNav(appKey).catch(err => {
      console.error("[Login] Failed to load grouped nav:", err);
    });
  }

  await showMandirSplash();
  try {
    const checks = runChecks();
    const loadingBudget = delay(8000).then(() => ({ timedOut: true }));
    const result = await Promise.race([
      checks.then(() => ({ timedOut: false })),
      loadingBudget,
    ]);
    await delay(700);
    if (result.timedOut) {
      checks.catch((error) => {
        console.error("[Login] Background workspace load failed:", error);
      });
      setLoginStatus("warn", "Workspace is still loading", "Dashboard checks are continuing in the background.");
    }
  } finally {
    hideMandirSplash();
  }
}

export function _showPasswordError(msg) {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "block";
  if (passwordStatus) {
    passwordStatus.className = "module-state danger";
    passwordStatus.innerHTML = msg;
  }
}

export function _clearPasswordError() {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "none";
  if (passwordStatus) {
    passwordStatus.className = "module-state";
    passwordStatus.textContent = "";
  }
}

export async function updateCurrentPassword() {
  const currentPassword = String(currentPasswordInput?.value || "");
  const newPassword = String(newPasswordInput?.value || "");
  const confirmPassword = String(confirmNewPasswordInput?.value || "");
  const submitButton = document.getElementById("change-password-submit");

  if (!currentPassword || currentPassword.length < 6) {
    _showPasswordError("<strong>Current password required</strong><span>Enter the current account password first.</span>");
    return;
  }
  if (!newPassword || newPassword.length < 6) {
    _showPasswordError("<strong>New password too short</strong><span>Use at least 6 characters.</span>");
    return;
  }
  if (newPassword !== confirmPassword) {
    _showPasswordError("<strong>Passwords do not match</strong><span>Confirm the new password again.</span>");
    return;
  }
  _clearPasswordError();

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Updating...";
  }
  const result = await apiRequest(getAppKey(), "/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Update Password";
  }

  if (result.ok) {
    const wasForcedPasswordChange = pendingForcedPasswordChange;
    pendingForcedPasswordChange = false;
    passwordForm?.reset();
    if (passwordStatus) {
      passwordStatus.className = "module-state ok";
      passwordStatus.innerHTML = "<strong>Password updated</strong><span>Use the new password for your next sign-in.</span>";
    }
    passwordDialog?.close();
    if (wasForcedPasswordChange) {
      setLoginStatus("ok", "Password updated", "Password changed. Loading your MitraBooks workspace.");
      await completeWorkspaceSignIn(getExperienceAppKeys()[getCurrentExperience()] || getAppKey());
    } else {
      setLoginStatus("ok", "Password updated", "Use the new password for your next sign-in.");
    }
  } else {
    _showPasswordError(`<strong>Password update failed</strong><span>${escapeHtml(statusDetailText(result.payload?.detail) || statusDetailText(result.payload) || "Try again.")}</span>`);
  }
  renderJson(apiOutput, { change_password: { ok: result.ok, status: result.status, detail: result.payload?.detail } });
}

export function activeOrgSelectorType(context = getLastModuleContext()) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  return getSelectedOrgType() || organizationType || "BUSINESS";
}

export function syncOrgSelectorOptions(orgType) {
  document.querySelectorAll(".org-option").forEach((option) => {
    option.classList.toggle("active", option.getAttribute("data-org") === orgType);
  });
}

export function updateTrustedContextUi(context = getLastModuleContext()) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  const selectorOrgType = activeOrgSelectorType(context);
  const selectorMeta = getOrgSelectorMeta()[selectorOrgType] || getOrgSelectorMeta().BUSINESS;
  const tenantLabel = context?.tenant_name || context?.organization_name || context?.tenant_id || "";
  const enabledCount = Array.isArray(context?.enabled_modules)
    ? context.enabled_modules.length
    : Array.isArray(context?.modules)
      ? context.modules.filter((module) => module.enabled !== false).length
      : 0;

  if (currentOrgType) {
    currentOrgType.textContent = selectorMeta.label;
  }
  if (currentOrgTenant) {
    currentOrgTenant.textContent = selectorOrgType === "BUSINESS"
      ? tenantLabel || selectorMeta.subtitle
      : selectorMeta.subtitle;
  }
  syncOrgSelectorOptions(selectorOrgType);
  if (sidebarUserRole && getAccessToken()) {
    const role = context?.role || context?.user_role || "";
    sidebarUserRole.textContent = role || (enabledCount ? `${enabledCount} enabled module(s)` : "Tenant context loaded");
  }
}

export async function signInWithPassword() {
  const email = String(loginEmail?.value || "").trim().toLowerCase();
  const password = String(loginPassword?.value || "");
  const loginSubmitBtn = document.getElementById("login-submit");
  const errorField = document.getElementById("login-error-field");
  const errorMessage = document.getElementById("login-error-message");

  // Validate input
  if (!email || !password) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Email and password are required.";
    }
    setLoginStatus("warn", "Email and password required", "Enter your MitraBooks tenant admin login.");
    return;
  }

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Please enter a valid email address.";
    }
    setLoginStatus("warn", "Invalid email", "Email must be a valid email address.");
    return;
  }

  // Clear previous errors
  if (errorField) {
    errorField.hidden = true;
  }

  // Disable button and show loading state
  if (loginSubmitBtn) {
    loginSubmitBtn.disabled = true;
    loginSubmitBtn.textContent = "Signing in...";
  }

  try {
    setLoginStatus("", "Signing in", "Checking your tenant access...");
    const appKey = getExperienceAppKeys()[getCurrentExperience()] || getAppKey();
    const result = await apiRequest(appKey, "/api/v1/auth/login", {
      method: "POST",
      timeoutMs: getLoginRequestTimeoutMs(),
      body: JSON.stringify({ email, password }),
    });

    if (!result.ok) {
      clearAccessToken();
      updateSessionUi();
      const detail = statusDetailText(result.payload?.detail) ||
        statusDetailText(result.payload) ||
        "Unable to sign in with these credentials.";

      // Show error message in form
      if (errorField && errorMessage) {
        errorField.hidden = false;
        errorMessage.textContent = detail;
      }

      setLoginStatus("danger", "Sign in failed", detail);
      renderJson(apiOutput, { login: { ok: result.ok, status: result.status, detail } });
      return;
    }

    // Successful login
    setAccessToken(result.payload?.access_token || "");
    setRefreshToken(result.payload?.refresh_token || "");
    window.localStorage.setItem(getLoginEmailStorageKey(), email);

    // Clear password for security
    if (loginPassword) {
      loginPassword.value = "";
    }

    updateSessionUi();
    renderJson(apiOutput, { login: { ok: true, status: result.status, token_type: result.payload?.token_type || "bearer" } });
    const currentUser = await loadCurrentUserProfile(appKey);
    pendingForcedPasswordChange = Boolean(currentUser?.must_change_password);
    if (pendingForcedPasswordChange) {
      setLoginStatus("warn", "Temporary password in use", "Change the temporary password to continue into the MitraBooks workspace.");
      openPasswordDialog();
      return;
    }
    setLoginStatus("ok", "Signed in", "Tenant workspace is loading.");
    await completeWorkspaceSignIn(appKey);
  } catch (error) {
    console.error("[Login] Error during sign in:", error);
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "An unexpected error occurred. Please try again.";
    }
    setLoginStatus("danger", "Sign in error", "An unexpected error occurred. Please try again.");
  } finally {
    // Re-enable button
    if (loginSubmitBtn) {
      loginSubmitBtn.disabled = false;
      loginSubmitBtn.textContent = "Sign in";
    }
  }
}


export function isPasswordRecoveryPanelOpen() {
  const forgotOpen = Boolean(forgotPasswordForm && !forgotPasswordForm.hasAttribute("hidden"));
  const resetOpen = Boolean(resetPasswordForm && !resetPasswordForm.hasAttribute("hidden"));
  return forgotOpen || resetOpen;
}

export function setAuthPanelMode(mode) {
  const normalized = mode === "forgot" || mode === "reset" ? mode : "login";
  const title = document.getElementById("access-title");
  const copy = document.getElementById("access-copy");
  const loginForm = document.getElementById("login-form");
  loginForm?.toggleAttribute("hidden", normalized !== "login");
  forgotPasswordForm?.toggleAttribute("hidden", normalized !== "forgot");
  resetPasswordForm?.toggleAttribute("hidden", normalized !== "reset");
  if (title) {
    title.textContent = normalized === "forgot"
      ? "Reset password"
      : normalized === "reset"
        ? "Set new password"
        : "Sign in";
  }
  if (copy) {
    copy.textContent = normalized === "forgot"
      ? "Enter your MitraBooks account email. If it exists, a reset link will be sent."
      : normalized === "reset"
        ? "Choose a new password for your MitraBooks account."
        : "Use your tenant admin credentials to open the workspace.";
  }
}

export function showAuthFieldMessage(fieldId, message) {
  const field = document.getElementById(fieldId);
  const messageNode = field?.querySelector("p");
  if (field) field.hidden = false;
  if (messageNode) messageNode.textContent = message;
}

export function clearAuthFieldMessage(fieldId) {
  const field = document.getElementById(fieldId);
  const messageNode = field?.querySelector("p");
  if (field) field.hidden = true;
  if (messageNode) messageNode.textContent = "";
}

export async function requestPasswordReset() {
  const email = String(forgotPasswordEmail?.value || loginEmail?.value || "").trim().toLowerCase();
  const submitButton = document.getElementById("forgot-password-submit");
  clearAuthFieldMessage("forgot-error-field");
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showAuthFieldMessage("forgot-error-field", "Enter a valid account email.");
    setLoginStatus("warn", "Email required", "Enter the MitraBooks account email to request a reset link.");
    return;
  }
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Sending...";
  }
  const result = await apiRequest(getAppKey(), "/api/v1/auth/forgot-password", {
    method: "POST",
    timeoutMs: getLoginRequestTimeoutMs(),
    body: JSON.stringify({ email }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Send reset link";
  }
  if (result.ok) {
    window.localStorage.setItem(getLoginEmailStorageKey(), email);
    if (loginEmail) loginEmail.value = email;
    setLoginStatus("ok", "Reset link requested", result.payload?.message || "If this account exists, password reset instructions have been sent.");
  } else {
    const detail = statusDetailText(result.payload?.detail) || "Password reset email could not be sent. Please try again.";
    showAuthFieldMessage("forgot-error-field", detail);
    setLoginStatus("danger", "Reset request failed", detail);
  }
  renderJson(apiOutput, { forgot_password: { ok: result.ok, status: result.status } });
}

export async function completePasswordReset() {
  const newPassword = String(resetNewPasswordInput?.value || "");
  const confirmPassword = String(resetConfirmPasswordInput?.value || "");
  const submitButton = document.getElementById("reset-password-submit");
  clearAuthFieldMessage("reset-error-field");
  if (!getPendingPasswordResetToken()) {
    showAuthFieldMessage("reset-error-field", "Reset token is missing or expired. Request a new reset link.");
    return;
  }
  if (newPassword.length < 6) {
    showAuthFieldMessage("reset-error-field", "Password must be at least 6 characters.");
    return;
  }
  if (newPassword !== confirmPassword) {
    showAuthFieldMessage("reset-error-field", "Password and confirm password do not match.");
    return;
  }
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Updating...";
  }
  const result = await apiRequest(getAppKey(), "/api/v1/auth/reset-password", {
    method: "POST",
    timeoutMs: getLoginRequestTimeoutMs(),
    body: JSON.stringify({
      token: getPendingPasswordResetToken(),
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Update password";
  }
  if (result.ok) {
    setPendingPasswordResetToken("");
    resetPasswordForm?.reset();
    if (window.history?.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    setAuthPanelMode("login");
    setLoginStatus("ok", "Password updated", "Use the new password to sign in.");
  } else {
    const detail = statusDetailText(result.payload?.detail) || "Password could not be updated. Request a new reset link.";
    showAuthFieldMessage("reset-error-field", detail);
    setLoginStatus("danger", "Password reset failed", detail);
  }
  renderJson(apiOutput, { reset_password: { ok: result.ok, status: result.status } });
}

