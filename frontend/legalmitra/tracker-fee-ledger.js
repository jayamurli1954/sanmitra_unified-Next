/* LegalMitra Tracker — Stage 6 fee ledger: summary, issue, collect, void */

function feeErrorDetail(result) {
  const payload = result?.payload;
  if (typeof payload === "string" && payload.trim()) return payload;
  if (payload && typeof payload === "object") {
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((row) => (typeof row === "string" ? row : row?.msg || JSON.stringify(row)))
        .join("; ");
    }
    if (payload.message) return String(payload.message);
    return JSON.stringify(payload);
  }
  return `HTTP ${result?.status || 0}`;
}

function newIdempotencyKey(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createFeeLedgerController({
  apiRequest,
  getAccessToken,
  appKey,
  getLivePractice,
  onSummaryLoaded,
}) {
  let feeSummary = null;
  let feeInvoices = [];

  function statusEl() {
    return document.getElementById("fee-ledger-live-summary");
  }

  async function loadFeeLedger() {
    const panel = document.getElementById("fee-ledger-live");
    const listEl = document.getElementById("fee-ledger-live-list");
    const summaryEl = statusEl();
    if (!getAccessToken()) {
      feeSummary = null;
      feeInvoices = [];
      if (panel) panel.hidden = true;
      return;
    }
    try {
      const [summaryRes, invoicesRes] = await Promise.all([
        apiRequest(appKey, "/api/v1/legal/practice/fees/summary", {
          method: "GET",
          timeoutMs: 12000,
        }),
        apiRequest(appKey, "/api/v1/legal/practice/fees/invoices?limit=20", {
          method: "GET",
          timeoutMs: 12000,
        }),
      ]);
      feeSummary = summaryRes?.ok ? summaryRes.payload : null;
      feeInvoices = invoicesRes?.ok ? invoicesRes.payload.items || [] : [];
      if (summaryRes && !summaryRes.ok && summaryRes.status === 503) {
        feeSummary = null;
        feeInvoices = [];
      }
    } catch (_error) {
      feeSummary = null;
      feeInvoices = [];
    }

    if (!panel || !listEl || !summaryEl) return;
    panel.hidden = false;
    if (feeSummary) {
      summaryEl.textContent =
        `Outstanding ${feeSummary.fees_outstanding_display || "₹0.00"} · ` +
        `billed ${feeSummary.total_billed ?? 0} · collected ${feeSummary.total_collected ?? 0}`;
      const live = getLivePractice?.();
      if (live) {
        live.fees_outstanding =
          feeSummary.fees_outstanding_display || live.fees_outstanding;
      }
      onSummaryLoaded?.(feeSummary);
    } else {
      summaryEl.textContent =
        "Fee ledger unavailable (billing may be disabled for this environment).";
    }

    listEl.textContent = "";
    const actionsHost = document.getElementById("fee-ledger-live-actions");
    if (actionsHost) actionsHost.textContent = "";

    if (!feeInvoices.length) {
      const li = document.createElement("li");
      li.textContent =
        "No fee notes yet. Use Issue/Collect below after creating a draft via API, or refresh after billing is enabled.";
      listEl.appendChild(li);
      return;
    }

    feeInvoices.slice(0, 12).forEach((inv) => {
      const li = document.createElement("li");
      li.textContent =
        `${inv.invoice_number || inv.invoice_id} · ${inv.status} · ` +
        `due ${inv.amount_outstanding ?? "—"} / total ${inv.grand_total ?? "—"}`;
      listEl.appendChild(li);
    });

    if (!actionsHost) return;
    const draft = feeInvoices.find((i) => i.status === "draft");
    const collectable = feeInvoices.find((i) =>
      ["issued", "partially_paid"].includes(i.status),
    );
    const voidable = feeInvoices.find((i) => i.status === "draft" || i.status === "issued");

    const addBtn = (label, onClick) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = label;
      btn.addEventListener("click", onClick);
      actionsHost.appendChild(btn);
    };
    if (draft) {
      addBtn(`Issue ${draft.invoice_number || "draft"}`, () => issueInvoice(draft.invoice_id));
    }
    if (collectable) {
      addBtn(`Collect ${collectable.invoice_number || "fee"}`, () =>
        collectPayment(collectable),
      );
    }
    if (voidable && voidable.status === "draft") {
      addBtn(`Void ${voidable.invoice_number || "draft"}`, () => voidInvoice(voidable.invoice_id));
    }
  }

  async function issueInvoice(invoiceId) {
    const summaryEl = statusEl();
    if (summaryEl) summaryEl.textContent = "Issuing fee note…";
    const result = await apiRequest(
      appKey,
      `/api/v1/legal/practice/fees/invoices/${encodeURIComponent(invoiceId)}/issue`,
      { method: "POST", timeoutMs: 20000 },
    );
    if (!result?.ok) {
      if (summaryEl) {
        summaryEl.textContent = `Could not issue: ${feeErrorDetail(result)}`;
      }
      return;
    }
    await loadFeeLedger();
  }

  async function collectPayment(invoice) {
    const outstanding = String(invoice.amount_outstanding ?? invoice.grand_total ?? "");
    const amount = window.prompt(
      `Collection amount for ${invoice.invoice_number || invoice.invoice_id} (outstanding ${outstanding}):`,
      outstanding,
    );
    if (!amount || !String(amount).trim()) return;
    const summaryEl = statusEl();
    if (summaryEl) summaryEl.textContent = "Recording collection…";
    const result = await apiRequest(
      appKey,
      `/api/v1/legal/practice/fees/invoices/${encodeURIComponent(invoice.invoice_id)}/collections`,
      {
        method: "POST",
        timeoutMs: 20000,
        body: JSON.stringify({
          amount: String(amount).trim(),
          mode: "bank",
          idempotency_key: newIdempotencyKey("ui-collect"),
          post_to_mitrabooks: false,
          confirm_post_to_mitrabooks: false,
        }),
      },
    );
    if (!result?.ok) {
      if (summaryEl) {
        summaryEl.textContent = `Could not collect: ${feeErrorDetail(result)}`;
      }
      return;
    }
    await loadFeeLedger();
  }

  async function voidInvoice(invoiceId) {
    const reason = window.prompt("Void reason (required for audit):", "Created in error");
    if (!reason || reason.trim().length < 2) return;
    const summaryEl = statusEl();
    if (summaryEl) summaryEl.textContent = "Voiding fee note…";
    const result = await apiRequest(
      appKey,
      `/api/v1/legal/practice/fees/invoices/${encodeURIComponent(invoiceId)}/void`,
      {
        method: "POST",
        timeoutMs: 20000,
        body: JSON.stringify({ reason: reason.trim(), confirm: true }),
      },
    );
    if (!result?.ok) {
      if (summaryEl) {
        summaryEl.textContent = `Could not void: ${feeErrorDetail(result)}`;
      }
      return;
    }
    await loadFeeLedger();
  }

  return {
    loadFeeLedger,
    getFeeSummary: () => feeSummary,
    clear() {
      feeSummary = null;
      feeInvoices = [];
    },
  };
}
