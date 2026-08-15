import { apiRequest, clearAccessToken, getAccessToken, setAccessToken } from "../shared/api-client.js";

const APP_KEY = "legalmitra";
const SESSION_KEY = "LEGALMITRA_AUTH_SESSION";

const statusNode = document.getElementById("login-status");
const loginPanel = document.getElementById("login-panel");
const registerPanel = document.getElementById("register-panel");
const forgotPanel = document.getElementById("forgot-panel");
const actionPanel = document.getElementById("action-panel");
const sessionActions = document.getElementById("existing-session-actions");

const emailInput = document.getElementById("login-email");
const passwordInput = document.getElementById("login-password");
const emailLoginButton = document.getElementById("email-login-btn");
const googleLoginButton = document.getElementById("google-login-btn");
const googleSigninHost = document.getElementById("google-signin-button");

const openRegisterButton = document.getElementById("open-register-btn");
const closeRegisterButton = document.getElementById("close-register-btn");
const registerSendButton = document.getElementById("register-send-btn");
const regFullNameInput = document.getElementById("reg-full-name");
const regEmailInput = document.getElementById("reg-email");

const openForgotButton = document.getElementById("open-forgot-btn");
const closeForgotButton = document.getElementById("close-forgot-btn");
const forgotSendButton = document.getElementById("forgot-send-btn");
const forgotEmailInput = document.getElementById("forgot-email");

const actionTitle = document.getElementById("action-title");
const actionPasswordInput = document.getElementById("action-password");
const actionConfirmPasswordInput = document.getElementById("action-confirm-password");
const actionSubmitButton = document.getElementById("action-submit-btn");

const continueSessionButton = document.getElementById("continue-session-btn");
const logoutSessionButton = document.getElementById("logout-session-btn");

const params = new URLSearchParams(window.location.search);
const flowAction = String(params.get("action") || "").trim().toLowerCase();
const flowToken = String(params.get("token") || "").trim();
let runtimeGoogleClientId = "";
let googleInitialized = false;

function returnTarget() {
  const target = String(params.get("return") || params.get("next") || "./chat.html").trim();
  if (!target || target.startsWith("http://") || target.startsWith("https://") || target.startsWith("//")) {
    return "./chat.html";
  }
  return target;
}

function showStatus(message, tone = "ok") {
  statusNode.textContent = message;
  statusNode.className = `legal-auth-status ${tone === "err" ? "err" : "ok"}`;
}

function clearStatus() {
  statusNode.textContent = "";
  statusNode.className = "legal-auth-status";
}

function setMode(mode) {
  const selected = String(mode || "login");
  loginPanel.hidden = selected !== "login";
  registerPanel.hidden = selected !== "register";
  forgotPanel.hidden = selected !== "forgot";
  actionPanel.hidden = selected !== "action";
  sessionActions.hidden = true;
}

function persistSession(payload) {
  setAccessToken(payload?.access_token || "");
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({
    access_token: payload?.access_token || "",
    refresh_token: payload?.refresh_token || "",
    token_type: payload?.token_type || "bearer",
    saved_at: new Date().toISOString(),
  }));
  localStorage.removeItem(SESSION_KEY);
}

function clearSession() {
  clearAccessToken();
  sessionStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(SESSION_KEY);
}

function safeRedirect(target = returnTarget()) {
  window.location.assign(target);
}

async function postJson(path, payload) {
  const result = await apiRequest(APP_KEY, path, {
    method: "POST",
    timeoutMs: 20000,
    body: JSON.stringify(payload || {}),
  });
  if (!result.ok) {
    throw new Error(result.payload?.detail || result.payload?.message || `Request failed (${result.status})`);
  }
  return result.payload || {};
}

async function acceptLegalTerms() {
  await apiRequest(APP_KEY, "/api/v1/users/accept-terms", { method: "POST" });
}

async function hasValidExistingSession() {
  if (!getAccessToken()) return false;
  const result = await apiRequest(APP_KEY, "/api/v1/auth/validate", { method: "GET" });
  if (result.ok) return true;
  clearSession();
  return false;
}

function showExistingSessionOptions() {
  showStatus("Existing login session found. You can continue, open chat, or logout before signing in with another account.", "ok");
  sessionActions.hidden = false;
}

async function loginWithEmail() {
  clearStatus();
  const email = String(emailInput.value || "").trim().toLowerCase();
  const password = String(passwordInput.value || "");
  if (!email || !password) {
    showStatus("Please enter email and password.", "err");
    return;
  }

  emailLoginButton.disabled = true;
  try {
    const tokenPayload = await postJson("/api/v1/auth/login", { email, password });
    persistSession(tokenPayload);
    passwordInput.value = "";
    await acceptLegalTerms();
    showStatus("Email login successful. Redirecting...", "ok");
    window.setTimeout(() => safeRedirect(), 350);
  } catch (error) {
    showStatus(`Email login failed: ${error.message}`, "err");
  } finally {
    emailLoginButton.disabled = false;
  }
}

async function registerUser() {
  clearStatus();
  const fullName = String(regFullNameInput.value || "").trim();
  const email = String(regEmailInput.value || "").trim().toLowerCase();
  if (fullName.length < 2 || !email.includes("@")) {
    showStatus("Please enter full name and a valid email address.", "err");
    return;
  }

  registerSendButton.disabled = true;
  try {
    const data = await postJson("/api/v1/auth/register-request", {
      full_name: fullName,
      email,
      role: "operator",
    });
    let message = "Activation link sent. Please check your email inbox.";
    if (data.activation_link_debug) message += `\n\nDebug Link:\n${data.activation_link_debug}`;
    if (data.email_delivery_error) message += `\n\nEmail delivery note: ${data.email_delivery_error}`;
    showStatus(message, "ok");
    setMode("login");
  } catch (error) {
    showStatus(`Registration failed: ${error.message}`, "err");
  } finally {
    registerSendButton.disabled = false;
  }
}

async function forgotPassword() {
  clearStatus();
  const email = String(forgotEmailInput.value || "").trim().toLowerCase();
  if (!email.includes("@")) {
    showStatus("Please enter a valid email address.", "err");
    return;
  }

  forgotSendButton.disabled = true;
  try {
    const data = await postJson("/api/v1/auth/forgot-password", { email });
    let message = "If your account exists, a reset link has been sent to your email.";
    if (data.reset_link_debug) message += `\n\nDebug Link:\n${data.reset_link_debug}`;
    if (data.email_delivery_error) message += `\n\nEmail delivery note: ${data.email_delivery_error}`;
    showStatus(message, "ok");
    setMode("login");
  } catch (error) {
    showStatus(`Forgot-password failed: ${error.message}`, "err");
  } finally {
    forgotSendButton.disabled = false;
  }
}

async function submitActionPassword() {
  clearStatus();
  const password = String(actionPasswordInput.value || "");
  const confirmPassword = String(actionConfirmPasswordInput.value || "");
  if (!flowToken) {
    showStatus("Missing token in link.", "err");
    return;
  }
  if (password.length < 6 || password !== confirmPassword) {
    showStatus("Password must be at least 6 characters and both entries must match.", "err");
    return;
  }

  actionSubmitButton.disabled = true;
  try {
    if (flowAction === "activate") {
      await postJson("/api/v1/auth/activate", { token: flowToken, password, confirm_password: confirmPassword });
      showStatus("Account activated successfully. Please login with email/password.", "ok");
    } else if (flowAction === "reset") {
      await postJson("/api/v1/auth/reset-password", { token: flowToken, new_password: password, confirm_password: confirmPassword });
      showStatus("Password reset successful. Please login with your new password.", "ok");
    } else {
      showStatus("Invalid action link.", "err");
      return;
    }
    window.setTimeout(() => window.location.assign("./login.html"), 1000);
  } catch (error) {
    showStatus(`Action failed: ${error.message}`, "err");
  } finally {
    actionSubmitButton.disabled = false;
  }
}

async function loadGoogleConfig() {
  const result = await apiRequest(APP_KEY, "/api/v1/auth/google-config", { method: "GET" });
  if (result.ok && result.payload?.client_id) {
    runtimeGoogleClientId = String(result.payload.client_id || "").trim();
  }
}

async function submitGoogleCredential(body) {
  // Returning users: never send a hardcoded tenant — the account's tenant wins.
  // First-time Google users need an approved onboarding_request_id (invite flow).
  const payload = { ...body };
  const onboardingRequestId = String(params.get("onboarding_request_id") || "").trim();
  if (onboardingRequestId) {
    payload.onboarding_request_id = onboardingRequestId;
  }
  const tokenPayload = await postJson("/api/v1/auth/google", payload);
  persistSession(tokenPayload);
  await acceptLegalTerms();
  showStatus("Google login successful. Redirecting...", "ok");
  window.setTimeout(() => safeRedirect(), 350);
}

function describeGoogleLoginError(error) {
  const detail = String(error?.message || "");
  if (detail.includes("approved onboarding")) {
    return "This Google account is not linked to a LegalMitra tenant yet. Use Register, or open your approved invite link, then try Google login again.";
  }
  if (detail.includes("App key mismatch")) {
    return "Google login failed: this Google account is not entitled for LegalMitra on its tenant. Use Login With Google and choose the subscribed account.";
  }
  return `Google login failed: ${detail}`;
}

function clearStickyGoogleAccount() {
  try {
    window.google?.accounts?.id?.disableAutoSelect?.();
    window.google?.accounts?.id?.cancel?.();
  } catch (_error) {
    // Ignore GIS cancel/disable errors on unsupported browsers.
  }
  if (googleSigninHost) {
    googleSigninHost.innerHTML =
      '<p class="legal-auth-google-hint">Previous Google profile cleared. Tap <strong>Login With Google</strong> and choose the subscribed account.</p>';
  }
}

async function ensureGoogleReady(renderButton = true) {
  if (!runtimeGoogleClientId) await loadGoogleConfig();
  if (!runtimeGoogleClientId) return { ok: false, reason: "config" };
  if (!(window.google?.accounts?.id)) return { ok: false, reason: "script" };

  if (!googleInitialized) {
    window.google.accounts.id.initialize({
      client_id: runtimeGoogleClientId,
      auto_select: false,
      cancel_on_tap_outside: true,
      callback: async (response) => {
        if (!response?.credential) {
          showStatus("Google token not received.", "err");
          return;
        }
        try {
          await submitGoogleCredential({ id_token: response.credential });
        } catch (error) {
          clearStickyGoogleAccount();
          showStatus(describeGoogleLoginError(error), "err");
        }
      },
    });
    googleInitialized = true;
  }

  if (renderButton && googleSigninHost) {
    // Do not auto-render the sticky "Continue as …" button — it locks to the
    // last browser Google profile. Account choice happens via Login With Google.
    googleSigninHost.innerHTML =
      '<p class="legal-auth-google-hint">Tap <strong>Login With Google</strong> to pick the correct Google account.</p>';
  }
  return { ok: true };
}

async function loginWithGoogle() {
  clearStatus();
  if (!runtimeGoogleClientId) await loadGoogleConfig();
  if (!runtimeGoogleClientId) {
    showStatus("Google login is not configured in backend environment variables.", "err");
    return;
  }
  if (!(window.google?.accounts?.oauth2?.initTokenClient)) {
    showStatus("Google Sign-In script did not load. Refresh and try again.", "err");
    return;
  }

  clearStickyGoogleAccount();
  googleLoginButton.disabled = true;
  showStatus("Choose the subscribed Google account in the popup…", "ok");

  try {
    const tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: runtimeGoogleClientId,
      scope: "openid email profile",
      prompt: "select_account",
      callback: async (tokenResponse) => {
        googleLoginButton.disabled = false;
        if (tokenResponse?.error) {
          clearStickyGoogleAccount();
          showStatus(`Google login failed: ${tokenResponse.error}`, "err");
          return;
        }
        if (!tokenResponse?.access_token) {
          showStatus("Google token not received.", "err");
          return;
        }
        try {
          await submitGoogleCredential({ access_token: tokenResponse.access_token });
        } catch (error) {
          clearStickyGoogleAccount();
          showStatus(describeGoogleLoginError(error), "err");
        }
      },
      error_callback: (error) => {
        googleLoginButton.disabled = false;
        const message = String(error?.type || error?.message || "popup_closed");
        if (message === "popup_closed") {
          showStatus("Google sign-in cancelled.", "err");
          return;
        }
        showStatus(`Google login failed: ${message}`, "err");
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  } catch (error) {
    googleLoginButton.disabled = false;
    showStatus(describeGoogleLoginError(error), "err");
  }
}

function initActionFlow() {
  if (!flowAction || !flowToken) return false;
  if (flowAction !== "activate" && flowAction !== "reset") {
    showStatus("Invalid link action.", "err");
    return true;
  }
  setMode("action");
  actionTitle.textContent = flowAction === "activate" ? "Activate Account - Set Password" : "Reset Password";
  actionSubmitButton.textContent = flowAction === "activate" ? "Activate Account" : "Reset Password";
  actionSubmitButton.addEventListener("click", submitActionPassword);
  return true;
}

function initLoginFlow() {
  setMode("login");
  emailLoginButton.addEventListener("click", loginWithEmail);
  passwordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loginWithEmail();
    }
  });
  openRegisterButton.addEventListener("click", () => {
    clearStatus();
    setMode("register");
  });
  closeRegisterButton.addEventListener("click", () => {
    clearStatus();
    setMode("login");
  });
  registerSendButton.addEventListener("click", registerUser);
  openForgotButton.addEventListener("click", () => {
    clearStatus();
    setMode("forgot");
  });
  closeForgotButton.addEventListener("click", () => {
    clearStatus();
    setMode("login");
  });
  forgotSendButton.addEventListener("click", forgotPassword);
  googleLoginButton.addEventListener("click", loginWithGoogle);
  googleLoginButton.disabled = true;
  loadGoogleConfig().then(() => ensureGoogleReady(true)).finally(() => {
    googleLoginButton.disabled = false;
  });
  continueSessionButton.addEventListener("click", () => safeRedirect());
  logoutSessionButton.addEventListener("click", () => {
    clearSession();
    sessionActions.hidden = true;
    showStatus("Session cleared. You can login again now.", "ok");
  });
  hasValidExistingSession().then((valid) => {
    if (valid) showExistingSessionOptions();
  });
}

if (!initActionFlow()) {
  initLoginFlow();
}
