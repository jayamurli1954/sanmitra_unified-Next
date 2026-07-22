// ══════════════════════════════════════════════════════════════════════
// SECTION: WIDGET SYSTEM (dashboard widget collapse / visibility / settings)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Dashboard re-render deps are injected via
// initWidgets(...) so this module does not import app.js (avoids cycles).
// ══════════════════════════════════════════════════════════════════════

export const WIDGET_STATES_STORAGE_KEY = "mitrabooks-widget-states";
export const DEFAULT_WIDGET_STATES = {
  "kpi-strip": { visible: true, collapsed: false, order: 1 },
  "finance-chart": { visible: true, collapsed: false, order: 2 },
  "ceo-panel": { visible: true, collapsed: false, order: 3 }
};

/** @type {{
 *   escapeHtml: (value: string) => string,
 *   getExperience: () => string,
 *   getWorkspace: () => string,
 *   renderExecutiveDashboard: () => string,
 * } | null} */
let deps = null;

/**
 * Inject app.js callbacks used when widget visibility/reset re-renders the dashboard.
 * Must be called once during app bootstrap before widget UI is used.
 */
export function initWidgets({
  escapeHtml,
  getExperience,
  getWorkspace,
  renderExecutiveDashboard,
}) {
  deps = {
    escapeHtml,
    getExperience,
    getWorkspace,
    renderExecutiveDashboard,
  };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initWidgets() must be called before using the widget system");
  }
  return deps;
}

/**
 * Get all widget states from localStorage
 */
export function getWidgetStates() {
  try {
    const saved = localStorage.getItem(WIDGET_STATES_STORAGE_KEY);
    return saved ? JSON.parse(saved) : JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES));
  } catch (e) {
    console.warn("Failed to parse widget states, using defaults", e);
    return JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES));
  }
}

/**
 * Save widget states to localStorage
 */
export function saveWidgetStates(states) {
  try {
    localStorage.setItem(WIDGET_STATES_STORAGE_KEY, JSON.stringify(states));
  } catch (e) {
    console.warn("Failed to save widget states", e);
  }
}

/**
 * Get state of a specific widget
 */
export function getWidgetState(widgetId) {
  const states = getWidgetStates();
  return states[widgetId] || { visible: true, collapsed: false };
}

/**
 * Toggle collapse state of a widget
 */
export function toggleWidgetCollapse(widgetId) {
  const states = getWidgetStates();
  if (states[widgetId]) {
    states[widgetId].collapsed = !states[widgetId].collapsed;
    saveWidgetStates(states);
    applyWidgetCollapse(widgetId, states[widgetId].collapsed);
  }
}

/**
 * Toggle visibility of a widget and re-render the settings panel + dashboard
 */
export function toggleWidgetVisibility(widgetId) {
  const { getExperience, getWorkspace, renderExecutiveDashboard } = requireDeps();
  const states = getWidgetStates();
  if (states[widgetId]) {
    states[widgetId].visible = !states[widgetId].visible;
    saveWidgetStates(states);
    // Refresh the settings panel checkboxes in-place
    const panel = document.getElementById("widget-settings-panel");
    if (panel) {
      const checkbox = panel.querySelector(`input[data-widget-id="${widgetId}"]`);
      if (checkbox) checkbox.checked = states[widgetId].visible;
    }
    // Re-render dashboard widgets in place
    if (getExperience() === "mitrabooks" && getWorkspace() === "overview") {
      const execDash = document.querySelector(".executive-dashboard");
      if (execDash) {
        const tmp = document.createElement("div");
        tmp.innerHTML = renderExecutiveDashboard();
        execDash.replaceWith(tmp.firstElementChild);
      }
    }
  }
}

/**
 * Reset all widgets to default state
 */
export function resetWidgetStates() {
  const { getExperience, getWorkspace, renderExecutiveDashboard } = requireDeps();
  saveWidgetStates(JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES)));
  closeWidgetSettings();
  if (getExperience() === "mitrabooks" && getWorkspace() === "overview") {
    const execDash = document.querySelector(".executive-dashboard");
    if (execDash) {
      const tmp = document.createElement("div");
      tmp.innerHTML = renderExecutiveDashboard();
      execDash.replaceWith(tmp.firstElementChild);
    }
  }
}

/**
 * Open the widget customization settings panel
 */
export function openWidgetSettings() {
  const existing = document.getElementById("widget-settings-overlay");
  if (existing) { existing.remove(); return; }

  const overlay = document.createElement("div");
  overlay.id = "widget-settings-overlay";
  overlay.className = "widget-settings-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Dashboard widget settings");

  overlay.innerHTML = renderWidgetSettingsPanel();
  document.body.appendChild(overlay);

  // Close on click outside the panel
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) { closeWidgetSettings(); return; }
    const btn = e.target.closest("[data-widget-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-widget-action");
    if (action === "close-settings") closeWidgetSettings();
    else if (action === "reset-widgets") resetWidgetStates();
  });

  // Toggle visibility on checkbox change
  overlay.addEventListener("change", (e) => {
    const input = e.target.closest("input[data-widget-action='toggle-visibility']");
    if (input) toggleWidgetVisibility(input.getAttribute("data-widget-id") || "");
  });

  // Close on Escape key
  const onKey = (e) => {
    if (e.key === "Escape") { closeWidgetSettings(); document.removeEventListener("keydown", onKey); }
  };
  document.addEventListener("keydown", onKey);

  const firstFocus = overlay.querySelector("button, input");
  if (firstFocus) firstFocus.focus();
}

/**
 * Close the widget settings panel
 */
export function closeWidgetSettings() {
  const overlay = document.getElementById("widget-settings-overlay");
  if (overlay) overlay.remove();
}

/**
 * Render the widget settings panel HTML
 */
export function renderWidgetSettingsPanel() {
  const { escapeHtml } = requireDeps();
  const states = getWidgetStates();
  const widgetLabels = {
    "kpi-strip":     "Key Performance Indicators",
    "finance-chart": "Sales & Expenses Trend",
    "ceo-panel":     "CEO Insights"
  };

  const rows = Object.entries(widgetLabels).map(([id, label]) => {
    const visible = states[id]?.visible !== false;
    return `
      <label class="widget-settings-row">
        <span class="widget-settings-label">${escapeHtml(label)}</span>
        <input
          type="checkbox"
          class="widget-settings-toggle"
          data-widget-action="toggle-visibility"
          data-widget-id="${id}"
          ${visible ? "checked" : ""}
          aria-label="Show ${escapeHtml(label)}"
        >
        <span class="widget-settings-switch" aria-hidden="true"></span>
      </label>
    `;
  }).join("");

  return `
    <div id="widget-settings-panel" class="widget-settings-panel">
      <div class="widget-settings-header">
        <h4>Dashboard Widgets</h4>
        <button class="widget-settings-close" data-widget-action="close-settings" aria-label="Close settings">✕</button>
      </div>
      <p class="widget-settings-hint">Toggle which widgets appear on your executive dashboard.</p>
      <div class="widget-settings-list">
        ${rows}
      </div>
      <div class="widget-settings-footer">
        <button class="secondary" type="button" data-widget-action="reset-widgets">Reset to Defaults</button>
      </div>
    </div>
  `;
}

/**
 * Apply collapse/expand animation to widget
 */
export function applyWidgetCollapse(widgetId, isCollapsed) {
  const widget = document.getElementById(`widget-${widgetId}`);
  const btn = document.getElementById(`collapse-btn-${widgetId}`);

  if (widget) {
    widget.classList.toggle("collapsed", isCollapsed);
  }
  if (btn) {
    btn.textContent = isCollapsed ? "⌄" : "⌃";
    btn.setAttribute("aria-label", isCollapsed ? "Expand widget" : "Collapse widget");
  }
}

/**
 * Create widget wrapper HTML with header controls
 */
export function createWidgetWrapper(widgetId, title, content, showControls = true) {
  const { escapeHtml } = requireDeps();
  const state = getWidgetState(widgetId);
  const isCollapsed = state.collapsed;
  const isVisible = state.visible !== false;

  if (!isVisible) {
    return ""; // Don't render hidden widgets
  }

  const collapseBtnHtml = showControls ? `
    <button
      id="collapse-btn-${widgetId}"
      class="widget-collapse-btn"
      data-business-action="widget-collapse"
      data-widget-id="${widgetId}"
      aria-label="${isCollapsed ? 'Expand widget' : 'Collapse widget'}"
      title="${isCollapsed ? 'Expand' : 'Collapse'}"
    >
      ${isCollapsed ? "⌄" : "⌃"}
    </button>
  ` : "";

  return `
    <div id="widget-${widgetId}" class="dashboard-widget ${isCollapsed ? 'collapsed' : ''}" data-widget-id="${widgetId}">
      <div class="widget-header">
        <h4>${escapeHtml(title)}</h4>
        ${showControls ? `<div class="widget-header-controls">${collapseBtnHtml}</div>` : ""}
      </div>
      <div class="widget-content">
        ${content}
      </div>
    </div>
  `;
}
