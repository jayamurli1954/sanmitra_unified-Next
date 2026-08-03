/* LegalMitra Tracker — document custody (P0) helpers */

export const CUSTODY_LABELS = {
  cloud_minimized: "Personal Practice",
  chamber_lan: "Chamber LAN",
};

export function createCustodyController({ apiRequest, getAccessToken, appKey, getLivePractice, setLivePracticeDocCustody }) {
  let custodySettings = null;

  function renderCustodyPanel() {
    const badge = document.getElementById("custody-badge");
    const badgeLabel = document.getElementById("custody-badge-label");
    const panel = document.getElementById("custody-panel");
    const copyEl = document.getElementById("custody-panel-copy");
    const questionEl = document.getElementById("custody-onboarding-question");
    const statusEl = document.getElementById("custody-status");
    const saveBtn = document.getElementById("custody-save");
    if (!badge || !panel) return;

    if (!getAccessToken() || !custodySettings) {
      badge.hidden = true;
      panel.hidden = true;
      return;
    }

    const mode = custodySettings.doc_custody_mode || "cloud_minimized";
    const label =
      custodySettings.display_name ||
      CUSTODY_LABELS[mode] ||
      "Personal Practice";
    badge.hidden = false;
    if (badgeLabel) badgeLabel.textContent = label;
    panel.hidden = false;

    if (questionEl && custodySettings.onboarding_question) {
      questionEl.textContent = custodySettings.onboarding_question;
    }
    if (copyEl) {
      const guidance =
        (custodySettings.mode_guidance && custodySettings.mode_guidance[mode]) ||
        "LegalMitra manages document custody according to your chamber’s operating model.";
      copyEl.textContent = guidance;
    }

    document.querySelectorAll('input[name="custody-mode"]').forEach((input) => {
      input.checked = input.value === mode;
      input.disabled = !custodySettings.can_manage;
    });

    if (saveBtn) {
      saveBtn.hidden = !custodySettings.can_manage;
    }
    if (statusEl && !statusEl.dataset.sticky) {
      statusEl.textContent = custodySettings.can_manage
        ? "Choose Personal Practice or Chamber LAN, then save. This does not upload case papers."
        : "Ask a chamber admin to change document custody mode.";
    }
  }

  async function loadCustodySettings(livePractice) {
    if (!getAccessToken()) {
      custodySettings = null;
      renderCustodyPanel();
      return;
    }
    try {
      const result = await apiRequest(appKey, "/api/v1/legal/practice/custody-settings", {
        method: "GET",
        timeoutMs: 12000,
      });
      custodySettings = result?.ok ? result.payload : null;
    } catch (_error) {
      custodySettings = livePractice?.doc_custody
        ? {
            ...livePractice.doc_custody,
            can_manage: false,
            onboarding_question:
              "Does this chamber use a shared office file server for case papers?",
            mode_guidance: {},
          }
        : null;
    }
    renderCustodyPanel();
  }

  async function saveCustodySettings() {
    const statusEl = document.getElementById("custody-status");
    const selected = document.querySelector('input[name="custody-mode"]:checked');
    if (!selected || !custodySettings?.can_manage) return;
    if (statusEl) {
      statusEl.dataset.sticky = "1";
      statusEl.textContent = "Saving custody mode…";
    }
    try {
      const result = await apiRequest(appKey, "/api/v1/legal/practice/custody-settings", {
        method: "PATCH",
        timeoutMs: 12000,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          doc_custody_mode: selected.value,
          onboarding_answered: true,
        }),
      });
      if (!result?.ok) {
        const detail = result?.payload?.detail;
        const message = Array.isArray(detail)
          ? detail.map((d) => d.msg || d).join("; ")
          : detail || result?.payload?.message || "Could not save custody settings";
        throw new Error(message);
      }
      custodySettings = result.payload;
      setLivePracticeDocCustody?.({
        doc_custody_mode: custodySettings.doc_custody_mode,
        display_name: custodySettings.display_name,
        doc_cloud_originals_opt_in: custodySettings.doc_cloud_originals_opt_in,
        chamber_connector_enabled: custodySettings.chamber_connector_enabled,
        onboarding_answered: custodySettings.onboarding_answered,
      });
      if (statusEl) {
        statusEl.textContent = `Saved — Document custody: ${custodySettings.display_name}.`;
      }
      renderCustodyPanel();
    } catch (error) {
      if (statusEl) {
        statusEl.textContent = error?.message || "Could not save custody settings.";
      }
    }
  }

  function clearCustodySettings() {
    custodySettings = null;
    renderCustodyPanel();
  }

  return {
    renderCustodyPanel,
    loadCustodySettings,
    saveCustodySettings,
    clearCustodySettings,
  };
}
