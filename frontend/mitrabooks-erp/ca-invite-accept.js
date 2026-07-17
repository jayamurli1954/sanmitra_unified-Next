import { apiRequest, clearAllTokens } from "../shared/api-client.js";

const params = new URLSearchParams(window.location.search);
const token = String(params.get("token") || "").trim();
const form = document.getElementById("ca-invite-form");
const nameEl = document.getElementById("invite-name");
const emailEl = document.getElementById("invite-email");
const tenantEl = document.getElementById("invite-tenant");
const statusEl = document.getElementById("invite-status");
const fullNameInput = document.getElementById("full-name");
const passwordInput = document.getElementById("password");
const confirmPasswordInput = document.getElementById("confirm-password");
const submitButton = document.getElementById("accept-submit");

function setStatus(tone, message) {
  statusEl.dataset.tone = tone;
  statusEl.textContent = message;
}

function invitePath(suffix) {
  return `/api/v1/business/ca/invite/${encodeURIComponent(token)}${suffix}`;
}

function detailText(payload, fallback) {
  if (payload && typeof payload === "object" && payload.detail) return String(payload.detail);
  if (typeof payload === "string" && payload.trim()) return payload.trim();
  return fallback;
}

async function loadInvite() {
  clearAllTokens();
  if (!token) {
    nameEl.textContent = "Invite link is missing a token";
    setStatus("danger", "Use the full invite link from your email.");
    return;
  }

  const result = await apiRequest("mitrabooks", invitePath("/preview"), {
    method: "GET",
    timeoutMs: 10000,
  });

  if (!result.ok) {
    nameEl.textContent = "Invite unavailable";
    emailEl.textContent = "";
    tenantEl.textContent = "";
    setStatus("danger", detailText(result.payload, "This invite is invalid, expired, or already used."));
    return;
  }

  const payload = result.payload || {};
  const maskedEmail = String(payload.masked_email || "").trim();
  nameEl.textContent = "Chartered Accountant invitation";
  emailEl.textContent = maskedEmail ? `Email: ${maskedEmail}` : "";
  tenantEl.textContent = "";
  form.hidden = false;
  setStatus("warn", "Create a password to activate read-only CA access.");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = String(passwordInput.value || "");
  const confirmPassword = String(confirmPasswordInput.value || "");
  const fullName = String(fullNameInput.value || "").trim();

  if (password.length < 8) {
    setStatus("danger", "Use a password with at least 8 characters.");
    return;
  }
  if (password !== confirmPassword) {
    setStatus("danger", "Passwords do not match.");
    return;
  }

  submitButton.disabled = true;
  setStatus("warn", "Accepting invite...");
  const result = await apiRequest("mitrabooks", invitePath("/accept"), {
    method: "POST",
    body: JSON.stringify({ password, full_name: fullName || undefined }),
    timeoutMs: 15000,
  });
  passwordInput.value = "";
  confirmPasswordInput.value = "";
  submitButton.disabled = false;

  if (!result.ok) {
    setStatus("danger", detailText(result.payload, "Invite acceptance failed."));
    return;
  }

  form.hidden = true;
  setStatus("ok", "Invite accepted. You can now sign in with your email and password.");
});

loadInvite();
