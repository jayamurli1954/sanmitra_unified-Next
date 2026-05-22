const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "sanmitra_frontend_api_base_url";

const apiBaseInput = document.getElementById("api-base");
const loadTemplesButton = document.getElementById("load-temples");
const templeSelect = document.getElementById("temple-select");
const templeInfo = document.getElementById("temple-info");
const paymentType = document.getElementById("payment-type");
const purposeSelect = document.getElementById("purpose-select");
const amountInput = document.getElementById("amount");
const previewUpiButton = document.getElementById("preview-upi");
const paymentPreview = document.getElementById("payment-preview");
const apiOutput = document.getElementById("api-output");

let temples = [];
let selectedTempleInfo = null;
let donationCategories = [];
let sevas = [];

function normalizeApiBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function getRuntimeApiBaseUrl() {
  const params = new URLSearchParams(window.location.search);
  const queryApi = normalizeApiBaseUrl(params.get("api"));
  if (queryApi) {
    localStorage.setItem(API_BASE_STORAGE_KEY, queryApi);
    return queryApi;
  }
  const stored = normalizeApiBaseUrl(localStorage.getItem(API_BASE_STORAGE_KEY));
  if (stored) {
    return stored;
  }
  const host = String(window.location.hostname || "").toLowerCase();
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "::1") {
    return LOCAL_API_BASE_URL;
  }
  return "/api";
}

function buildApiUrl(path) {
  const base = normalizeApiBaseUrl(apiBaseInput.value || getRuntimeApiBaseUrl());
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (base === "/api" && normalizedPath.startsWith("/api/")) {
    return normalizedPath;
  }
  if (base.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${base.slice(0, -4)}${normalizedPath}`;
  }
  return `${base}${normalizedPath}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function renderJson(value) {
  apiOutput.textContent = JSON.stringify(value, null, 2);
}

async function publicRequest(path) {
  const response = await fetch(buildApiUrl(path), {
    method: "GET",
    headers: { "X-App-Key": "mandirmitra" },
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  const result = { ok: response.ok, status: response.status, payload };
  renderJson(result);
  return result;
}

function optionLabel(item) {
  return [item.temple_name || item.trust_name || `Temple ${item.temple_id}`, item.city, item.state]
    .filter(Boolean)
    .join(" - ");
}

function isDemoTemple(item) {
  const text = [
    item?.temple_name,
    item?.trust_name,
    item?.upi_payee_name,
  ].filter(Boolean).join(" ").toLowerCase();
  return text.includes("demo") || text.includes("test");
}

function renderTempleOptions() {
  if (!temples.length) {
    templeSelect.innerHTML = `<option value="">No public temples configured</option>`;
    return;
  }
  templeSelect.innerHTML = [
    `<option value="">Select temple/trust</option>`,
    ...temples.map((temple) => {
      const marker = isDemoTemple(temple) ? "Demo/Test - " : "";
      return `<option value="${escapeHtml(temple.temple_id)}">${escapeHtml(`${marker}${optionLabel(temple)}`)}</option>`;
    }),
  ].join("");
}

function renderTempleInfo() {
  if (!selectedTempleInfo) {
    templeInfo.className = "module-state";
    templeInfo.innerHTML = "No temple selected.";
    return;
  }
  const enabled = Boolean(selectedTempleInfo.upi_public_enabled && selectedTempleInfo.upi_id);
  const demoMarker = isDemoTemple(selectedTempleInfo) ? `<span class="pill ok">Demo/Test tenant</span>` : `<span class="pill warn">Live trust: visibility only in staging</span>`;
  templeInfo.className = `module-state ${enabled ? "ok" : "warn"}`;
  templeInfo.innerHTML = `
    <strong>${escapeHtml(selectedTempleInfo.temple_name || selectedTempleInfo.trust_name || "Temple")}</strong>
    ${demoMarker}
    <span>${escapeHtml([selectedTempleInfo.trust_name, selectedTempleInfo.city, selectedTempleInfo.state].filter(Boolean).join(" - "))}</span>
    <span>UPI: ${escapeHtml(selectedTempleInfo.upi_id || "not configured")}</span>
    <span>Payee: ${escapeHtml(selectedTempleInfo.upi_payee_name || "not configured")}</span>
  `;
}

function renderPurposes() {
  const isDonation = paymentType.value === "donation";
  const rows = isDonation ? donationCategories : sevas;
  if (!rows.length) {
    purposeSelect.innerHTML = `<option value="">No ${isDonation ? "donation categories" : "sevas"} configured</option>`;
    return;
  }
  purposeSelect.innerHTML = rows.map((row) => {
    const name = isDonation ? row.name : row.seva_name;
    const amount = row.amount ? ` - Rs. ${row.amount}` : "";
    return `<option value="${escapeHtml(name || "")}">${escapeHtml(`${name || "Purpose"}${amount}`)}</option>`;
  }).join("");
}

async function loadPublicTemples() {
  localStorage.setItem(API_BASE_STORAGE_KEY, normalizeApiBaseUrl(apiBaseInput.value));
  templeInfo.className = "module-state";
  templeInfo.innerHTML = "Loading public temples...";
  const result = await publicRequest("/api/v1/public/temples");
  temples = result.ok && Array.isArray(result.payload) ? result.payload : [];
  renderTempleOptions();
  selectedTempleInfo = null;
  donationCategories = [];
  sevas = [];
  renderTempleInfo();
  renderPurposes();
}

async function loadTempleDetails() {
  const templeId = templeSelect.value;
  selectedTempleInfo = null;
  donationCategories = [];
  sevas = [];
  renderTempleInfo();
  renderPurposes();
  if (!templeId) {
    return;
  }
  const info = await publicRequest(`/api/v1/public/temples/${encodeURIComponent(templeId)}/info`);
  selectedTempleInfo = info.ok ? info.payload : null;
  const categories = await publicRequest(`/api/v1/public/temples/${encodeURIComponent(templeId)}/donation-categories`);
  donationCategories = categories.ok && Array.isArray(categories.payload) ? categories.payload : [];
  const sevaResult = await publicRequest(`/api/v1/public/temples/${encodeURIComponent(templeId)}/sevas`);
  sevas = sevaResult.ok && Array.isArray(sevaResult.payload) ? sevaResult.payload : [];
  renderTempleInfo();
  renderPurposes();
}

async function previewUpiInstructions() {
  const templeId = templeSelect.value;
  const amount = Number(amountInput.value || 0);
  const purpose = String(purposeSelect.value || paymentType.value || "Temple Offering").trim();
  if (!templeId || !amount || amount <= 0) {
    paymentPreview.className = "module-state warn";
    paymentPreview.innerHTML = "<strong>Missing details</strong><span>Select a temple and enter an amount.</span>";
    return;
  }
  const query = new URLSearchParams({ amount: String(amount), purpose });
  const result = await publicRequest(`/api/v1/public/temples/${encodeURIComponent(templeId)}/upi-intent?${query}`);
  if (!result.ok) {
    paymentPreview.className = "module-state warn";
    paymentPreview.innerHTML = `<strong>UPI unavailable</strong><span>${escapeHtml(result.payload?.detail || "Public UPI is not configured.")}</span>`;
    return;
  }
  paymentPreview.className = "module-state ok";
  paymentPreview.innerHTML = `
    <strong>UPI instructions visible</strong>
    <span>Payee: ${escapeHtml(result.payload.upi_payee_name || "")}</span>
    <span>UPI ID: ${escapeHtml(result.payload.upi_id || "")}</span>
    <span>Amount: Rs. ${escapeHtml(result.payload.amount || amount)}</span>
    <a href="${escapeHtml(result.payload.intent_uri || "#")}">Open UPI app</a>
  `;
}

apiBaseInput.value = getRuntimeApiBaseUrl();
loadTemplesButton.addEventListener("click", loadPublicTemples);
templeSelect.addEventListener("change", loadTempleDetails);
paymentType.addEventListener("change", renderPurposes);
previewUpiButton.addEventListener("click", previewUpiInstructions);
loadPublicTemples();
