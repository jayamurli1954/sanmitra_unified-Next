// ====================================================================
// SECTION: PARTIES — CRUD + dialogs
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initParties(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessParties = [];
export let lastBusinessPartiesResult = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initParties(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initParties() must be called before using parties helpers");
  }
  return deps;
}

function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getBusinessListState() { return requireDeps().getBusinessListState(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export function setLastBusinessParties(value) {
  lastBusinessParties = Array.isArray(value) ? value : [];
}

export function setLastBusinessPartiesResult(value) {
  lastBusinessPartiesResult = value;
}

export function clearPartiesState() {
  lastBusinessParties = [];
  lastBusinessPartiesResult = null;
}

export async function loadBusinessParties(filters = {}) {
  const appKey = "mitrabooks";
  const state = getBusinessListState().parties;
  const params = new URLSearchParams();

  if (state.q) params.append("q", state.q);
  if (state.party_type) params.append("party_type", state.party_type);
  params.append("offset", state.offset || 0);
  params.append("limit", 20);

  const queryString = params.toString();
  const url = `/api/v1/business/parties${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  lastBusinessPartiesResult = result;
  if (result.ok) {
    lastBusinessParties = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "parties") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessParties = [];
    setLoginStatus("warn", "Unable to load parties", result.payload?.detail || "Check connection and try again.");
  }
  renderJson(getApiOutput(), { parties: { ok: result.ok, count: lastBusinessParties.length } });
  return result;
}


export async function createBusinessParty(data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    party_type: data.party_type,
    gstin: data.gstin || null,
    pan: data.pan?.trim().toUpperCase() || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
  };

  const result = await apiRequest(appKey, "/api/v1/business/parties", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party created", result.payload?.party_name || "New party added.");
    document.getElementById("business-party-create-dialog")?.close();
    await loadBusinessParties();
    // Force refresh of current workspace
    if (getActiveBusinessWorkspace() === "parties") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(getApiOutput(), { create_party: result });
}


export async function updateBusinessParty(partyId, data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    gstin: data.gstin || null,
    pan: data.pan?.trim().toUpperCase() || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
  };
  if (data.party_type) {
    payload.party_type = data.party_type;
  }

  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party updated", result.payload?.party_name || "Changes saved.");
    document.getElementById("business-party-edit-dialog")?.close();
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Update party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(getApiOutput(), { update_party: result });
}


export async function deactivateBusinessParty(partyId) {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}/deactivate`, {
    method: "POST",
  });

  if (result.ok) {
    setLoginStatus("ok", "Party deactivated", "Party is now inactive.");
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Deactivate party failed", result.payload?.detail || "Try again.");
  }
  renderJson(getApiOutput(), { deactivate_party: result });
}


export function openBusinessCreatePartyDialog() {
  const dialog = document.getElementById("business-party-create-dialog");
  const form = document.getElementById("business-party-create-form");
  if (!form) return;

  form.reset();
  dialog?.showModal();
}


export function openBusinessEditPartyDialog(button) {
  const dialog = document.getElementById("business-party-edit-dialog");
  const form = document.getElementById("business-party-edit-form");
  if (!form) return;

  const partyId = button.getAttribute("data-party-id") || "";
  const partyName = button.getAttribute("data-party-name") || "";
  const partyType = button.getAttribute("data-party-type") || "customer";
  const partyGstin = button.getAttribute("data-party-gstin") || "";
  const partyPan = button.getAttribute("data-party-pan") || "";
  const partyCity = button.getAttribute("data-party-city") || "";
  const partyState = button.getAttribute("data-party-state") || "";
  const partyPincode = button.getAttribute("data-party-pincode") || "";

  document.getElementById("business-party-edit-id").value = partyId;
  const editTypeSelect = document.getElementById("business-party-edit-type");
  if (editTypeSelect) editTypeSelect.value = partyType;
  document.getElementById("business-party-edit-name").value = partyName;
  document.getElementById("business-party-edit-gstin").value = partyGstin;
  const editPanInput = document.getElementById("business-party-edit-pan");
  if (editPanInput) editPanInput.value = partyPan;
  document.getElementById("business-party-edit-city").value = partyCity;
  document.getElementById("business-party-edit-state").value = partyState;
  document.getElementById("business-party-edit-pincode").value = partyPincode;
  document.getElementById("business-party-edit-label").textContent = `Editing ${partyName}`;

  dialog?.showModal();
}


