(() => {
  const staleText = "Income, expenses, and cash movement";

  const clean = () => {
    const widget = document.getElementById("widget-kpi-strip");
    if (!widget) {
      return;
    }
    widget.querySelectorAll("h1, h2, h3, h4, p, span").forEach((node) => {
      if ((node.textContent || "").trim() !== staleText) {
        return;
      }
      const block = node.closest(".kpi-widget-title-block") || node.parentElement;
      if (block && !block.classList.contains("executive-kpi-strip")) {
        block.remove();
      } else {
        node.remove();
      }
    });
  };

  clean();
  new MutationObserver(clean).observe(document.body, { childList: true, subtree: true });
})();
