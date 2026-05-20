const installStateKey = "sanmitra_pwa_install_prompt_seen";
const installDismissedKey = "sanmitra_pwa_install_prompt_dismissed";
const legalMitraInstallDismissedKey = "legalmitra_pwa_install_prompt_dismissed";
let installPromptRendered = false;

function setAppHeight() {
  document.documentElement.style.setProperty("--app-height", `${window.innerHeight}px`);
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
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

function isIosLikeDevice() {
  const ua = window.navigator.userAgent || "";
  const iPadOSDesktopMode = window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1;
  return /iphone|ipad|ipod/i.test(ua) || iPadOSDesktopMode;
}

function shouldShowInstallSuggestion() {
  if (!isLegalMitraPath() || isStandaloneMode()) {
    return false;
  }
  return !localStorage.getItem(legalMitraInstallDismissedKey);
}

function buildInstallCopy(hasNativePrompt) {
  if (hasNativePrompt) {
    return {
      title: "Install LegalMitra",
      body: "Use LegalMitra from your desktop, laptop, Android phone, or tablet with a standalone app window.",
      action: "Install",
    };
  }
  if (isIosLikeDevice()) {
    return {
      title: "Add LegalMitra to Home Screen",
      body: "On iPhone or iPad, tap Share in Safari, then choose Add to Home Screen.",
      action: "Got it",
    };
  }
  return {
    title: "Install LegalMitra",
    body: "Use the browser install option from the address bar or menu when it appears.",
    action: "Got it",
  };
}

function closeInstallSuggestion(panel) {
  localStorage.setItem(installDismissedKey, new Date().toISOString());
  localStorage.setItem(legalMitraInstallDismissedKey, new Date().toISOString());
  panel.remove();
  installPromptRendered = false;
}

function renderLegalMitraInstallSuggestion() {
  if (!shouldShowInstallSuggestion() || installPromptRendered || document.getElementById("legalmitra-install-suggestion")) {
    return;
  }

  const hasNativePrompt = Boolean(window.__SANMITRA_PWA_INSTALL_PROMPT__);
  if (!hasNativePrompt && !isIosLikeDevice()) {
    return;
  }
  const copy = buildInstallCopy(hasNativePrompt);
  const panel = document.createElement("section");
  panel.className = "legal-install-suggestion";
  panel.id = "legalmitra-install-suggestion";
  panel.setAttribute("aria-label", "Install LegalMitra");
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
