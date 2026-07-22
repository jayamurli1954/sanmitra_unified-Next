// ══════════════════════════════════════════════════════════════════════
// SECTION: THEME (dark / light)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged.
// ══════════════════════════════════════════════════════════════════════

export const THEME_STORAGE_KEY = "mitrabooks-theme";

/**
 * Set the app theme (dark or light)
 * Persists to localStorage for offline retention
 */
export function setTheme(theme) {
  const validTheme = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", validTheme);
  localStorage.setItem(THEME_STORAGE_KEY, validTheme);
  updateThemeButtons(validTheme);
}

/**
 * Get the current theme or user preference
 */
export function getTheme() {
  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  if (saved) {
    return saved;
  }

  // Check system preference
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }

  return "dark"; // Default to dark
}

/**
 * Initialize theme on app load
 */
export function initializeTheme() {
  const theme = getTheme();
  document.documentElement.setAttribute("data-theme", theme);
  updateThemeButtons(theme);
}

/**
 * Update UI buttons to show active theme
 */
export function updateThemeButtons(theme) {
  const darkBtn = document.getElementById("theme-dark-btn");
  const lightBtn = document.getElementById("theme-light-btn");

  if (darkBtn) {
    darkBtn.classList.toggle("active", theme === "dark");
  }
  if (lightBtn) {
    lightBtn.classList.toggle("active", theme === "light");
  }
}

/**
 * Listen for system theme changes (respects user's OS preference)
 */
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem(THEME_STORAGE_KEY)) {
      setTheme(e.matches ? "dark" : "light");
    }
  });
}
