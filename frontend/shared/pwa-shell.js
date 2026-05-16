const installStateKey = "sanmitra_pwa_install_prompt_seen";

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

function watchInstallPrompt() {
  window.addEventListener("beforeinstallprompt", (event) => {
    window.__SANMITRA_PWA_INSTALL_PROMPT__ = event;
    if (!localStorage.getItem(installStateKey)) {
      localStorage.setItem(installStateKey, new Date().toISOString());
    }
  });
}

setAppHeight();
markStandaloneMode();
registerServiceWorker();
watchInstallPrompt();

window.addEventListener("resize", setAppHeight);
window.addEventListener("orientationchange", () => {
  window.setTimeout(setAppHeight, 250);
});
