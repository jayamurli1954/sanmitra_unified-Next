(function bootstrapGruhaMitra() {
  function applyStyles(node, styles) {
    Object.assign(node.style, styles);
    return node;
  }

  function appendTextElement(parent, tagName, text, styles = {}) {
    const node = applyStyles(document.createElement(tagName), styles);
    node.textContent = String(text || "");
    parent.appendChild(node);
    return node;
  }

  function renderFailure({ title, message, errorMessage = "", errorStack = "" }) {
    const root = document.getElementById("root");
    if (!root) return;

    root.replaceChildren();
    const panel = applyStyles(document.createElement("div"), {
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh",
      fontFamily: "sans-serif",
      padding: "20px",
      textAlign: "center",
      background: "#fff",
      boxSizing: "border-box",
    });
    appendTextElement(panel, "h1", title, { color: "#ff4444", marginBottom: "20px" });
    appendTextElement(panel, "p", message, { color: "#666", fontSize: "18px", marginBottom: "10px" });

    if (errorMessage) {
      const detailsPanel = applyStyles(document.createElement("div"), {
        background: "#f5f5f5",
        padding: "15px",
        borderRadius: "8px",
        maxWidth: "800px",
        margin: "20px 0",
        textAlign: "left",
      });
      appendTextElement(detailsPanel, "strong", "Error Message:");
      appendTextElement(detailsPanel, "p", errorMessage, {
        color: "#ff4444",
        fontSize: "12px",
        wordBreak: "break-all",
      });
      if (errorStack) {
        const details = document.createElement("details");
        appendTextElement(details, "summary", "Show Full Error Details", { cursor: "pointer", color: "#007AFF" });
        appendTextElement(details, "pre", errorStack, {
          color: "#666",
          fontSize: "11px",
          overflowX: "auto",
          background: "#fff",
          padding: "10px",
          borderRadius: "4px",
          whiteSpace: "pre-wrap",
        });
        detailsPanel.appendChild(details);
      }
      panel.appendChild(detailsPanel);
    }

    const reloadButton = applyStyles(document.createElement("button"), {
      marginTop: "20px",
      padding: "12px 24px",
      background: "#007AFF",
      color: "white",
      border: "none",
      borderRadius: "6px",
      cursor: "pointer",
      fontSize: "14px",
      fontWeight: "bold",
    });
    reloadButton.type = "button";
    reloadButton.textContent = "Reload Page";
    reloadButton.addEventListener("click", () => window.location.reload());
    panel.appendChild(reloadButton);
    root.appendChild(panel);
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
        .catch((error) => console.warn("Service Worker cleanup failed", error));
    });
  }
  if ("caches" in window) {
    caches.keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .catch((error) => console.warn("Cache cleanup failed", error));
  }

  window.__REACT_MOUNTED__ = false;

  window.addEventListener("error", (event) => {
    if (window.__REACT_MOUNTED__) return;
    if (event.filename && (event.filename.includes("extension") || event.filename.includes("chext"))) return;
    if (!event.error && !event.message) return;

    console.error("GruhaMitra bootstrap error", event.error || event.message);
    renderFailure({
      title: "JavaScript Error",
      message: "GruhaMitra failed to load.",
      errorMessage: event.error ? String(event.error) : String(event.message || "Unknown error"),
      errorStack: event.error?.stack ? String(event.error.stack) : "",
    });
  }, true);

  window.addEventListener("load", () => {
    window.setTimeout(() => {
      if (window.__REACT_MOUNTED__) return;
      const applicationScript = document.querySelector('script[type="module"][src]');
      renderFailure({
        title: applicationScript ? "React Failed to Mount" : "Application Bundle Not Found",
        message: applicationScript
          ? "The application bundle loaded but React did not initialize."
          : "The application bundle is not loading.",
      });
    }, 5000);
  });
}());
