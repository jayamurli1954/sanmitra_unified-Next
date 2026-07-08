const installStateKey = "sanmitra_pwa_install_prompt_seen";
const installDismissedKey = "sanmitra_pwa_install_prompt_dismissed";
const legalMitraInstallDismissedKey = "legalmitra_pwa_install_prompt_dismissed";
const mitraBooksInstallDismissedKey = "mitrabooks_pwa_install_prompt_dismissed";
let installPromptRendered = false;

function setAppHeight() {
  document.documentElement.style.setProperty("--app-height", `${window.innerHeight}px`);
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  const host = String(window.location.hostname || "").toLowerCase();
  if (!host || host === "localhost" || host === "127.0.0.1" || host === "::1") {
    window.addEventListener("load", () => {
      navigator.serviceWorker.getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
        .catch(() => {});
      if ("caches" in window) {
        caches.keys()
          .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
          .catch(() => {});
      }
    });
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("../service-worker.js").catch(() => {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    });
  });
}

function markStandaloneMode() {
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;
  document.documentElement.dataset.displayMode = isStandalone ? "standalone" : "browser";
}

function isStandaloneMode() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function isLegalMitraPath() {
  return window.location.pathname.toLowerCase().includes("/legalmitra");
}

function isMitraBooksPath() {
  return window.location.pathname.toLowerCase().includes("/mitrabooks-erp");
}

function activeInstallApp() {
  if (isLegalMitraPath()) {
    return {
      id: "legalmitra",
      name: "LegalMitra",
      dismissedKey: legalMitraInstallDismissedKey,
      label: "Install LegalMitra",
    };
  }
  if (isMitraBooksPath()) {
    return {
      id: "mitrabooks",
      name: "MitraBooks",
      dismissedKey: mitraBooksInstallDismissedKey,
      label: "Install MitraBooks",
    };
  }
  return null;
}

function isIosLikeDevice() {
  const ua = window.navigator.userAgent || "";
  const iPadOSDesktopMode = window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1;
  return /iphone|ipad|ipod/i.test(ua) || iPadOSDesktopMode;
}

function shouldShowInstallSuggestion() {
  const app = activeInstallApp();
  if (!app || isStandaloneMode()) {
    return false;
  }
  return !localStorage.getItem(app.dismissedKey);
}

function buildInstallCopy(hasNativePrompt, app) {
  if (hasNativePrompt) {
    return {
      title: app.label,
      body: `Use ${app.name} from your desktop, Android phone, or tablet with a standalone app window.`,
      action: "Install",
    };
  }
  if (isIosLikeDevice()) {
    return {
      title: `Add ${app.name} to Home Screen`,
      body: "On iPhone or iPad, open Safari, tap Share, then choose Add to Home Screen.",
      action: "Got it",
    };
  }
  return {
    title: app.label,
    body: "Use the browser install option from the address bar or menu when it appears.",
    action: "Got it",
  };
}

function closeInstallSuggestion(panel) {
  const app = activeInstallApp();
  localStorage.setItem(installDismissedKey, new Date().toISOString());
  if (app) {
    localStorage.setItem(app.dismissedKey, new Date().toISOString());
  }
  panel.remove();
  installPromptRendered = false;
}

function renderLegalMitraInstallSuggestion() {
  const app = activeInstallApp();
  if (!app || !shouldShowInstallSuggestion() || installPromptRendered || document.getElementById("sanmitra-install-suggestion")) {
    return;
  }

  const hasNativePrompt = Boolean(window.__SANMITRA_PWA_INSTALL_PROMPT__);
  if (!hasNativePrompt && !isIosLikeDevice()) {
    return;
  }
  const copy = buildInstallCopy(hasNativePrompt, app);
  const panel = document.createElement("section");
  panel.className = "legal-install-suggestion sanmitra-install-suggestion";
  panel.id = "sanmitra-install-suggestion";
  panel.dataset.installApp = app.id;
  panel.setAttribute("aria-label", app.label);
  panel.innerHTML = `
    <div>
      <strong>${copy.title}</strong>
      <span>${copy.body}</span>
    </div>
    <div class="legal-install-actions">
      <button type="button" data-install-action>${copy.action}</button>
      <button type="button" data-install-dismiss aria-label="Dismiss install suggestion">x</button>
    </div>
  `;
  panel.querySelector("[data-install-dismiss]")?.addEventListener("click", () => closeInstallSuggestion(panel));
  panel.querySelector("[data-install-action]")?.addEventListener("click", async () => {
    const promptEvent = window.__SANMITRA_PWA_INSTALL_PROMPT__;
    if (promptEvent) {
      promptEvent.prompt();
      await promptEvent.userChoice.catch(() => null);
      window.__SANMITRA_PWA_INSTALL_PROMPT__ = null;
      closeInstallSuggestion(panel);
      return;
    }
    closeInstallSuggestion(panel);
  });
  document.body.appendChild(panel);
  installPromptRendered = true;
}

function watchInstallPrompt() {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    window.__SANMITRA_PWA_INSTALL_PROMPT__ = event;
    if (!localStorage.getItem(installStateKey)) {
      localStorage.setItem(installStateKey, new Date().toISOString());
    }
    renderLegalMitraInstallSuggestion();
  });
}

setAppHeight();
markStandaloneMode();
registerServiceWorker();
watchInstallPrompt();

window.addEventListener("load", () => {
  window.setTimeout(renderLegalMitraInstallSuggestion, 600);
});

window.addEventListener("resize", setAppHeight);
window.addEventListener("orientationchange", () => {
  window.setTimeout(setAppHeight, 250);
});
