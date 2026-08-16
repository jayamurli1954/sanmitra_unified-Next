/* LegalMitra Tracker — Stage 4 proactive surfaces: Morning Brief, alerts, notifications */

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatList(items) {
  if (!Array.isArray(items) || !items.length) return "<em>None</em>";
  return `<ul>${items.map((item) => {
    if (typeof item === "string") return `<li>${escapeHtml(item)}</li>`;
    const title = item.title || item.summary || item.matter_number || item.filename || "Item";
    return `<li>${escapeHtml(title)}</li>`;
  }).join("")}</ul>`;
}

export function parsePracticeDeepLink(url = window.location.href) {
  try {
    const parsed = new URL(url, window.location.origin);
    return {
      matterId: parsed.searchParams.get("matter_id") || "",
      focus: (parsed.hash || "").replace(/^#/, "") || "daily-board",
    };
  } catch {
    return { matterId: "", focus: "daily-board" };
  }
}

export function createProactiveController({
  apiRequest,
  getAccessToken,
  appKey,
  getCurrentRole,
  getMorningBrief,
  setMorningBrief,
  onStartWorkflow,
  onOpenMatter,
  onPracticeMutated,
}) {
  let alerts = [];
  let notifications = [];
  let proactiveDisabled = false;

  function els() {
    return {
      briefPanel: document.getElementById("morning-brief-panel"),
      healthEl: document.getElementById("morning-brief-health"),
      advisoryEl: document.getElementById("morning-brief-advisory"),
      actionsEl: document.getElementById("morning-brief-actions"),
      sectionsEl: document.getElementById("morning-brief-sections"),
      alertsPanel: document.getElementById("practice-alerts-panel"),
      alertsList: document.getElementById("practice-alerts-list"),
      alertsStatus: document.getElementById("practice-alerts-status"),
      alertsRefresh: document.getElementById("practice-alerts-refresh"),
      notesPanel: document.getElementById("practice-notifications-panel"),
      notesList: document.getElementById("practice-notifications-list"),
      notesStatus: document.getElementById("practice-notifications-status"),
    };
  }

  function setAlertsStatus(message) {
    const { alertsStatus } = els();
    if (alertsStatus) alertsStatus.textContent = message || "";
  }

  function setNotesStatus(message) {
    const { notesStatus } = els();
    if (notesStatus) notesStatus.textContent = message || "";
  }

  function renderMorningBrief() {
    const { briefPanel, healthEl, advisoryEl, actionsEl, sectionsEl } = els();
    if (!briefPanel || !healthEl || !actionsEl) return;

    if (!getAccessToken()) {
      briefPanel.hidden = true;
      return;
    }
    briefPanel.hidden = false;
    actionsEl.textContent = "";
    if (sectionsEl) sectionsEl.innerHTML = "";

    if (proactiveDisabled) {
      healthEl.textContent = "Proactive Assistant is disabled for this environment.";
      if (advisoryEl) {
        advisoryEl.hidden = false;
        advisoryEl.textContent =
          "LEGALMITRA_PROACTIVE_ENABLED / morning-brief flags are off. Stage 3 practice data still works.";
      }
      return;
    }

    const morningBrief = getMorningBrief?.();
    if (!morningBrief) {
      healthEl.textContent = "Morning Brief unavailable. Refresh after practice data is loaded.";
      if (advisoryEl) advisoryEl.hidden = true;
      return;
    }

    const score = morningBrief.practice_health_score;
    const label = morningBrief.practice_health_label || "";
    healthEl.textContent = `Practice Health ${score}/100 — ${label}`;
    if (advisoryEl) {
      advisoryEl.hidden = false;
      advisoryEl.textContent =
        morningBrief.advisory_notice ||
        "Advisory — human review required. Never invent hearings, statutes, or court dates.";
    }

    const actions = morningBrief.sections?.priority_actions || [];
    if (!actions.length) {
      const li = document.createElement("li");
      li.textContent = morningBrief.empty_practice
        ? "No practice data yet. Create a client and matter to activate Priority Actions."
        : "No open priority alerts for today.";
      actionsEl.appendChild(li);
    } else {
      actions.slice(0, 8).forEach((item) => {
        const li = document.createElement("li");
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "legal-proactive-open";
        openBtn.textContent = item.title || item.summary || "Open matter";
        openBtn.addEventListener("click", () => {
          onOpenMatter?.(item.matter_id, "matter-brief");
        });
        const meta = document.createElement("span");
        meta.textContent = ` · ${item.severity || "normal"} · score ${item.priority_score ?? "—"}`;
        const tip = document.createElement("div");
        tip.textContent = (item.suggested_actions || []).slice(0, 2).join(" · ");
        li.append(openBtn, meta);
        if (tip.textContent) li.appendChild(tip);

        const actionsRow = document.createElement("div");
        actionsRow.className = "legal-proactive-item-actions";
        const briefBtn = document.createElement("button");
        briefBtn.type = "button";
        briefBtn.textContent = "Matter brief";
        briefBtn.addEventListener("click", () => onOpenMatter?.(item.matter_id, "matter-brief"));
        const docsBtn = document.createElement("button");
        docsBtn.type = "button";
        docsBtn.textContent = "Documents";
        docsBtn.addEventListener("click", () => onOpenMatter?.(item.matter_id, "document-register"));
        actionsRow.append(briefBtn, docsBtn);
        li.appendChild(actionsRow);

        const wf = item.recommended_workflow;
        if (wf && item.matter_id && onStartWorkflow) {
          const start = document.createElement("button");
          start.type = "button";
          start.className = "legal-workflow-start";
          start.textContent = `Start: ${wf.display_name || "Prepare Matter Response"}`;
          start.addEventListener("click", (event) => {
            event.preventDefault();
            onStartWorkflow(item, start);
          });
          li.appendChild(start);
        }
        actionsEl.appendChild(li);
      });
    }

    if (sectionsEl) {
      const sections = morningBrief.sections || {};
      const blocks = [
        ["upcoming_hearings", "Upcoming Hearings"],
        ["upcoming_deadlines", "Upcoming Deadlines"],
        ["matters_awaiting_review", "Matters Awaiting Review"],
        ["compliance_gaps", "Compliance Gaps"],
        ["recent_activity", "Recent Activity"],
        ["suggested_focus", "Suggested Focus"],
        ["limitations", "Limitations"],
      ];
      sectionsEl.innerHTML = blocks
        .map(([key, label]) => {
          const value = sections[key];
          if (value == null || (Array.isArray(value) && !value.length)) {
            return `<section><h3>${escapeHtml(label)}</h3><em>None</em></section>`;
          }
          if (Array.isArray(value)) {
            return `<section><h3>${escapeHtml(label)}</h3>${formatList(value)}</section>`;
          }
          return `<section><h3>${escapeHtml(label)}</h3><p>${escapeHtml(value)}</p></section>`;
        })
        .join("");
      const conf = sections.confidence ?? morningBrief.confidence;
      const review = sections.human_review_required ?? morningBrief.human_review_required;
      sectionsEl.innerHTML += `<section><h3>Confidence / review</h3><p>Confidence: ${escapeHtml(
        String(conf ?? "—"),
      )} · Human review required: ${review === false ? "no" : "yes"}</p></section>`;
    }
  }

  function renderAlerts() {
    const { alertsPanel, alertsList } = els();
    if (!alertsPanel || !alertsList) return;
    if (!getAccessToken() || proactiveDisabled) {
      alertsPanel.hidden = true;
      return;
    }
    alertsPanel.hidden = false;
    alertsList.textContent = "";
    if (!alerts.length) {
      const li = document.createElement("li");
      li.textContent = "No open alerts. Refresh to re-evaluate deadlines and gaps.";
      alertsList.appendChild(li);
      return;
    }
    alerts.forEach((alert) => {
      const li = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = alert.title || alert.alert_type;
      const meta = document.createElement("div");
      meta.textContent = `${alert.severity || "normal"} · score ${alert.priority_score ?? "—"} · ${
        alert.summary || ""
      }`;
      const row = document.createElement("div");
      row.className = "legal-proactive-item-actions";
      const open = document.createElement("button");
      open.type = "button";
      open.textContent = "Open matter";
      open.disabled = !alert.matter_id;
      open.addEventListener("click", () => onOpenMatter?.(alert.matter_id, "matter-brief"));
      const snooze = document.createElement("button");
      snooze.type = "button";
      snooze.textContent = "Snooze 1 day";
      snooze.addEventListener("click", () => patchAlert(alert.alert_id, { status: "snoozed" }));
      const dismiss = document.createElement("button");
      dismiss.type = "button";
      dismiss.textContent = "Dismiss";
      dismiss.addEventListener("click", () => patchAlert(alert.alert_id, { status: "dismissed" }));
      row.append(open, snooze, dismiss);
      li.append(title, meta, row);
      alertsList.appendChild(li);
    });
  }

  function renderNotifications() {
    const { notesPanel, notesList } = els();
    if (!notesPanel || !notesList) return;
    if (!getAccessToken() || proactiveDisabled) {
      notesPanel.hidden = true;
      return;
    }
    notesPanel.hidden = false;
    notesList.textContent = "";
    if (!notifications.length) {
      const li = document.createElement("li");
      li.textContent = "No notifications yet.";
      notesList.appendChild(li);
      return;
    }
    notifications.forEach((note) => {
      const li = document.createElement("li");
      if (note.read_at) li.classList.add("is-read");
      const title = document.createElement("strong");
      title.textContent = note.title || "Notification";
      const body = document.createElement("div");
      body.textContent = note.body || "";
      const row = document.createElement("div");
      row.className = "legal-proactive-item-actions";
      const open = document.createElement("button");
      open.type = "button";
      open.textContent = "Open";
      open.addEventListener("click", () => {
        const deep = parsePracticeDeepLink(note.action_href || "./tracker.html#daily-board");
        if (deep.matterId) onOpenMatter?.(deep.matterId, deep.focus || "matter-brief");
        if (!note.read_at) markNotificationRead(note.notification_id);
      });
      if (!note.read_at) {
        const mark = document.createElement("button");
        mark.type = "button";
        mark.textContent = "Mark read";
        mark.addEventListener("click", () => markNotificationRead(note.notification_id));
        row.append(open, mark);
      } else {
        row.append(open);
      }
      li.append(title, body, row);
      notesList.appendChild(li);
    });
  }

  async function loadMorningBrief(forceRefresh) {
    if (!getAccessToken()) {
      setMorningBrief?.(null);
      proactiveDisabled = false;
      renderMorningBrief();
      return;
    }
    const persona =
      getCurrentRole?.() === "ca" || getCurrentRole?.() === "cs"
        ? getCurrentRole()
        : "advocate";
    try {
      const path = forceRefresh
        ? "/api/v1/legal/practice/morning-brief"
        : `/api/v1/legal/practice/morning-brief?persona=${encodeURIComponent(persona)}&window=daily`;
      const result = await apiRequest(appKey, path, {
        method: forceRefresh ? "POST" : "GET",
        timeoutMs: 20000,
        body: forceRefresh
          ? JSON.stringify({ persona, window: "daily", force_refresh: true })
          : undefined,
      });
      if (result?.status === 503) {
        proactiveDisabled = true;
        setMorningBrief?.(null);
      } else {
        proactiveDisabled = false;
        setMorningBrief?.(result?.ok ? result.payload : null);
      }
    } catch (_error) {
      setMorningBrief?.(null);
    }
    renderMorningBrief();
  }

  async function loadAlerts() {
    if (!getAccessToken() || proactiveDisabled) {
      alerts = [];
      renderAlerts();
      return;
    }
    try {
      const result = await apiRequest(appKey, "/api/v1/legal/practice/alerts?status=open&limit=20", {
        method: "GET",
        timeoutMs: 12000,
      });
      if (result?.status === 503) {
        proactiveDisabled = true;
        alerts = [];
      } else {
        alerts = result?.ok ? result.payload?.items || [] : [];
      }
    } catch (_error) {
      alerts = [];
    }
    renderAlerts();
  }

  async function refreshAlerts() {
    setAlertsStatus("Re-evaluating alerts…");
    const result = await apiRequest(appKey, "/api/v1/legal/practice/alerts/refresh", {
      method: "POST",
      timeoutMs: 20000,
      body: JSON.stringify({}),
    });
    if (result?.status === 503) {
      proactiveDisabled = true;
      setAlertsStatus("Proactive Assistant is disabled.");
      renderAlerts();
      return;
    }
    if (!result?.ok) {
      setAlertsStatus(`Refresh failed (${result?.status || "error"}).`);
      return;
    }
    setAlertsStatus(
      `Refreshed — ${result.payload?.open_alerts ?? "?"} open alerts (${
        result.payload?.created ?? 0
      } new).`,
    );
    await Promise.all([loadAlerts(), loadNotifications(), loadMorningBrief(true)]);
    await onPracticeMutated?.();
  }

  async function patchAlert(alertId, body) {
    setAlertsStatus("Updating alert…");
    const result = await apiRequest(
      appKey,
      `/api/v1/legal/practice/alerts/${encodeURIComponent(alertId)}`,
      {
        method: "PATCH",
        timeoutMs: 12000,
        body: JSON.stringify(body),
      },
    );
    if (!result?.ok) {
      setAlertsStatus(`Could not update alert (${result?.status || "error"}).`);
      return;
    }
    setAlertsStatus(`Alert ${body.status}.`);
    await Promise.all([loadAlerts(), loadMorningBrief(false)]);
    await onPracticeMutated?.();
  }

  async function loadNotifications() {
    if (!getAccessToken() || proactiveDisabled) {
      notifications = [];
      renderNotifications();
      return;
    }
    try {
      const result = await apiRequest(appKey, "/api/v1/legal/practice/notifications?limit=20", {
        method: "GET",
        timeoutMs: 12000,
      });
      if (result?.status === 503) {
        proactiveDisabled = true;
        notifications = [];
      } else {
        notifications = result?.ok ? result.payload?.items || [] : [];
      }
    } catch (_error) {
      notifications = [];
    }
    renderNotifications();
  }

  async function markNotificationRead(notificationId) {
    const result = await apiRequest(
      appKey,
      `/api/v1/legal/practice/notifications/${encodeURIComponent(notificationId)}/read`,
      { method: "PATCH", timeoutMs: 10000, body: JSON.stringify({}) },
    );
    if (!result?.ok) {
      setNotesStatus(`Could not mark read (${result?.status || "error"}).`);
      return;
    }
    setNotesStatus("Marked read.");
    await loadNotifications();
  }

  async function refreshAll() {
    await loadMorningBrief(false);
    await Promise.all([loadAlerts(), loadNotifications()]);
  }

  function bindEvents() {
    els().alertsRefresh?.addEventListener("click", () => refreshAlerts());
  }

  return {
    bindEvents,
    renderMorningBrief,
    loadMorningBrief,
    loadAlerts,
    loadNotifications,
    refreshAll,
    refreshAlerts,
  };
}
