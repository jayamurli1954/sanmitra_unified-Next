const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "sanmitra_public_onboarding_api_base_url";

const form = document.querySelector("[data-onboarding-form]");
const statusBox = document.querySelector("[data-onboarding-status]");
const submitButton = document.querySelector("[data-onboarding-submit]");

function normalizeApiBase(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function runtimeApiBase() {
  const params = new URLSearchParams(window.location.search);
  const queryApi = normalizeApiBase(params.get("api"));
  if (queryApi) {
    localStorage.setItem(API_BASE_STORAGE_KEY, queryApi);
    return queryApi;
  }
  const stored = normalizeApiBase(localStorage.getItem(API_BASE_STORAGE_KEY));
  if (stored) {
    return stored;
  }
  const host = String(window.location.hostname || "").toLowerCase();
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "::1") {
    return DEFAULT_API_BASE;
  }
  return "/api";
}

function apiUrl(path) {
  const base = normalizeApiBase(runtimeApiBase());
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (base === "/api" && normalizedPath.startsWith("/api/")) {
    return normalizedPath;
  }
  if (base.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${base.slice(0, -4)}${normalizedPath}`;
  }
  return `${base}${normalizedPath}`;
}

function setStatus(type, message) {
  statusBox.className = `onboarding-status ${type}`;
  statusBox.textContent = message;
}

function formValue(name) {
  const field = form.elements[name];
  return String(field?.value || "").trim();
}

function buildPayload() {
  const product = form.dataset.product || "SanMitra";
  const organizationName = formValue("organization_name");
  const organizationType = formValue("organization_type");
  const intent = formValue("request_intent") || "register";
  const termsAccepted = Boolean(form.elements.terms_accepted?.checked);
  const authorityDesignation = formValue("authority_designation");
  const payload = {
    organization_name: organizationName,
    organization_type: organizationType,
    authority_designation: authorityDesignation,
    authority_designation_other: authorityDesignation === "Other" ? formValue("authority_designation_other") : null,
    request_intent: intent,
    selected_plan: formValue("selected_plan") || null,
    plan_timing: formValue("plan_timing") || null,
    verification_channel: formValue("verification_channel") || "email",
    address: formValue("address") || null,
    phone: formValue("mobile") || null,
    email: formValue("email") || null,
    admin_full_name: formValue("full_name"),
    admin_email: formValue("email"),
    admin_phone: formValue("mobile") || null,
    terms_accepted: termsAccepted,
  };

  if (product === "MandirMitra") {
    payload.temple_name = organizationName;
    payload.trust_name = organizationName;
  }

  return payload;
}

function validatePayload(payload) {
  if (!payload.admin_full_name || !payload.admin_email || !payload.admin_phone || !payload.organization_name) {
    return "Full name, email address, mobile number, and organization name are required.";
  }
  if (!payload.authority_designation) {
    return "Designation or authority is required.";
  }
  if (payload.authority_designation === "Other" && !payload.authority_designation_other) {
    return "Please enter the designation or authority for Other.";
  }
  if (!payload.terms_accepted) {
    return "Please confirm authority and accept the Terms of Use and Privacy Policy.";
  }
  return "";
}

async function submitOnboarding(event) {
  event.preventDefault();
  const payload = buildPayload();
  const validationError = validatePayload(payload);
  if (validationError) {
    setStatus("warn", validationError);
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";
  try {
    const response = await fetch(apiUrl("/api/v1/onboarding-requests/register"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-App-Key": form.dataset.appKey || "mitrabooks",
      },
      body: JSON.stringify(payload),
    });
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = body?.detail || body?.message || body || "Unable to submit onboarding request.";
      throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg || item).join("; ") : detail);
    }
    setStatus(
      "ok",
      "Request submitted. Contact verification and plan/payment approval must be completed before login access is activated."
    );
    form.reset();
  } catch (error) {
    setStatus("warn", String(error?.message || "Unable to submit onboarding request."));
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Submit Request";
  }
}

if (form) {
  const params = new URLSearchParams(window.location.search);
  const intent = params.get("intent");
  if (intent && form.elements.request_intent) {
    form.elements.request_intent.value = intent === "demo" ? "demo" : "register";
  }
  const plan = params.get("plan");
  if (plan && form.elements.selected_plan) {
    form.elements.selected_plan.value = plan;
  }
  const authoritySelect = form.elements.authority_designation;
  const authorityOther = form.elements.authority_designation_other;
  const authorityOtherField = authorityOther?.closest(".onboarding-field");
  function syncAuthorityOtherField() {
    if (!authorityOther || !authorityOtherField) {
      return;
    }
    const isOther = authoritySelect?.value === "Other";
    authorityOtherField.hidden = !isOther;
    authorityOther.required = isOther;
    if (!isOther) {
      authorityOther.value = "";
    }
  }
  authoritySelect?.addEventListener("change", syncAuthorityOtherField);
  syncAuthorityOtherField();
  form.addEventListener("submit", submitOnboarding);
}
