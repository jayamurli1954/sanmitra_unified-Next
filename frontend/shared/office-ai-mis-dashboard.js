// MIS pack dashboard + attributed narrative (ADR-014).
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function factDimensions(fact) {
  const dims = fact?.dimensions;
  return dims && typeof dims === "object" ? dims : {};
}

function formatMisAmount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "—");
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatMisMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "—");
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toLocaleString("en-IN", { maximumFractionDigits: 2 })} Cr`;
  if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toLocaleString("en-IN", { maximumFractionDigits: 2 })} L`;
  return `${sign}₹${abs.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function resolveMisKpiUnit(item, fallbackUnit) {
  const raw = String(item?.unit || fallbackUnit || "");
  if (raw === "percent" || raw === "%") return "%";
  if (raw === "ratio") return "x";
  if (raw === "months") return "mo";
  return raw || fallbackUnit || "";
}

function formatMisKpiDisplay(item, fallbackUnit) {
  const unit = resolveMisKpiUnit(item, fallbackUnit);
  if (unit === "INR" || unit === "₹") return { display: formatMisMoney(item.value), unitLabel: "INR" };
  if (unit === "%") return { display: `${formatMisAmount(item.value)}%`, unitLabel: "percent" };
  if (unit === "x") return { display: formatMisAmount(item.value), unitLabel: "ratio" };
  if (unit === "days") return { display: formatMisAmount(item.value), unitLabel: "days" };
  if (unit === "mo") return { display: formatMisAmount(item.value), unitLabel: "months" };
  return { display: formatMisAmount(item.value), unitLabel: unit || "" };
}

function ensureMisDashboardStyles() {
  if (typeof document === "undefined") return;
  if (document.getElementById("office-ai-mis-dashboard-css")) return;
  const link = document.createElement("link");
  link.id = "office-ai-mis-dashboard-css";
  link.rel = "stylesheet";
  link.href = new URL("./office-ai-mis-dashboard.css", import.meta.url).href;
  document.head.appendChild(link);
}

export function buildMisDashboard(facts) {
  const items = Array.isArray(facts) ? facts : [];
  const kpis = {};
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "kpi") continue;
    const name = String(factDimensions(fact).kpi || fact.source_id || "").trim();
    if (!name) continue;
    kpis[name] = {
      value: fact.value,
      unit: String(factDimensions(fact).unit || ""),
    };
  }

  const ageing = { AR: {}, AP: {} };
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "aging_bucket") continue;
    const dims = factDimensions(fact);
    const side = String(dims.side || "").toUpperCase();
    const bucket = String(dims.bucket || "").trim();
    if ((side !== "AR" && side !== "AP") || !bucket) continue;
    ageing[side][bucket] = Number(fact.amount_decimal || 0);
  }

  const pnl = {};
  const revenueTrend = [];
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "pnl_line") continue;
    const dims = factDimensions(fact);
    const line = String(dims.line || "").trim();
    if (!line) continue;
    if (dims.trend) {
      if (line === "Revenue") {
        revenueTrend.push({
          period: String(fact.period || fact.as_of || ""),
          amount: Number(fact.amount_decimal || 0),
        });
      }
      continue;
    }
    pnl[line] = Number(fact.amount_decimal || 0);
  }
  revenueTrend.sort((a, b) => String(a.period).localeCompare(String(b.period)));

  const bs = {};
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "bs_line") continue;
    const line = String(factDimensions(fact).line || "").trim();
    if (!line) continue;
    bs[line] = Number(fact.amount_decimal || 0);
  }

  const cash = {};
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "cash_summary") continue;
    const line = String(factDimensions(fact).line || "").trim();
    if (!line) continue;
    cash[line] = Number(fact.amount_decimal || 0);
  }

  return { kpis, ageing, pnl, bs, cash, revenueTrend };
}

function renderMisAgeingColumnChart(side, buckets) {
  const order = ["Current", "1-30", "31-60", "61-90", "90+"];
  const values = order.map((b) => Number(buckets[b] || 0));
  const max = Math.max(...values, 1);
  const fillClass = side === "AR" ? "mis-bars__fill--ar" : "mis-bars__fill--ap";
  const cols = order
    .map((bucket, idx) => {
      const amount = values[idx];
      const pct = Math.max(4, Math.round((amount / max) * 100));
      return `<div class="mis-bars__col">
        <span class="mis-bars__amt" title="${escapeHtml(formatMisAmount(amount))}">${escapeHtml(formatMisMoney(amount))}</span>
        <div class="mis-bars__track"><div class="mis-bars__fill ${fillClass}" style="height:${pct}%;"></div></div>
        <span class="mis-bars__label">${escapeHtml(bucket)}</span>
      </div>`;
    })
    .join("");
  return `<article class="mis-panel">
    <h5 class="mis-panel__title">${side === "AR" ? "Receivables ageing" : "Payables ageing"}</h5>
    <div class="mis-bars">${cols}</div>
  </article>`;
}

function renderMisRevenueTrend(points) {
  if (!points.length) return "";
  const current = points[points.length - 1];
  const w = 320;
  const h = 120;
  const padX = 16;
  const padY = 18;
  const amounts = points.map((p) => Number(p.amount || 0));
  const min = Math.min(...amounts);
  const max = Math.max(...amounts);
  const span = Math.max(max - min, 1);
  const coords = points.map((p, i) => {
    const x = padX + (i / Math.max(points.length - 1, 1)) * (w - padX * 2);
    const y = h - padY - ((Number(p.amount) - min) / span) * (h - padY * 2);
    return { x, y, label: String(p.period || "").slice(0, 7), amount: p.amount };
  });
  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1].x.toFixed(1)},${(h - padY).toFixed(1)} L${coords[0].x.toFixed(1)},${(h - padY).toFixed(1)} Z`;
  const dots = coords
    .map((c) => `<circle class="mis-trend__point" cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="3.5"></circle>`)
    .join("");
  const labels = coords
    .map((c) => `<text class="mis-trend__axis" x="${c.x.toFixed(1)}" y="${h - 4}" text-anchor="middle">${escapeHtml(c.label)}</text>`)
    .join("");
  return `<article class="mis-panel">
    <h5 class="mis-panel__title">Revenue trend</h5>
    <svg class="mis-trend" viewBox="0 0 ${w} ${h}" role="img" aria-label="Revenue trend ${escapeHtml(formatMisMoney(current.amount))}">
      <path class="mis-trend__area" d="${area}"></path>
      <path class="mis-trend__line" d="${line}"></path>
      ${dots}
      ${labels}
    </svg>
  </article>`;
}

function renderMisPnlTable(pnl) {
  const order = ["Revenue", "COGS", "Gross Profit", "Operating Expenses", "EBIT", "Tax", "PAT"];
  const rows = order
    .filter((line) => pnl[line] != null)
    .map((line) => {
      const emph = line === "Revenue" || line === "Gross Profit" || line === "PAT" ? " emphasis" : "";
      return `<tr class="${emph}"><td>${escapeHtml(line)}</td><td class="num">${escapeHtml(formatMisMoney(pnl[line]))}</td></tr>`;
    })
    .join("");
  if (!rows) return "";
  return `<article class="mis-panel">
    <h5 class="mis-panel__title">P&amp;L snapshot</h5>
    <table class="mis-table">
      <thead><tr><th>Line</th><th style="text-align:right;">Amount</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </article>`;
}

function renderMisCashTable(cash) {
  const order = ["Operating", "Investing", "Financing", "Net Change"];
  const rows = order
    .filter((line) => cash[line] != null)
    .map((line) => {
      const emph = line === "Net Change" ? " emphasis" : "";
      return `<tr class="${emph}"><td>${escapeHtml(line)}</td><td class="num">${escapeHtml(formatMisMoney(cash[line]))}</td></tr>`;
    })
    .join("");
  if (!rows) return "";
  return `<article class="mis-panel">
    <h5 class="mis-panel__title">Cash flow summary</h5>
    <table class="mis-table">
      <thead><tr><th>Activity</th><th style="text-align:right;">Amount</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </article>`;
}

function renderMisPrimaryKpi(key, item, fallbackUnit, variant, label) {
  if (!item) return "";
  const { display, unitLabel } = formatMisKpiDisplay(item, fallbackUnit);
  return `<article class="mis-kpi mis-kpi--${escapeHtml(variant)}">
    <div class="mis-kpi__bar" aria-hidden="true"></div>
    <div class="mis-kpi__body">
      <div class="mis-kpi__label">${escapeHtml(label || key)}</div>
      <div class="mis-kpi__value">${escapeHtml(display)}</div>
      ${unitLabel ? `<div class="mis-kpi__unit">${escapeHtml(unitLabel)}</div>` : ""}
    </div>
  </article>`;
}

function renderMisChip(key, item, fallbackUnit, label) {
  if (!item) return "";
  const { display, unitLabel } = formatMisKpiDisplay(item, fallbackUnit);
  const suffix = unitLabel && unitLabel !== "INR" && unitLabel !== "percent" ? ` ${unitLabel}` : "";
  return `<div class="mis-chip">
    <span class="mis-chip__label">${escapeHtml(label || key)}</span>
    <span class="mis-chip__value">${escapeHtml(display)}${escapeHtml(suffix)}</span>
  </div>`;
}

export function renderMisDashboardStrip(facts) {
  ensureMisDashboardStyles();
  const dash = buildMisDashboard(facts);

  const primary = [
    renderMisPrimaryKpi("Revenue", dash.kpis.Revenue, "INR", "revenue", "Revenue"),
    renderMisPrimaryKpi("PAT", dash.kpis.PAT, "INR", "pat", "PAT"),
    renderMisPrimaryKpi("GrossMarginPct", dash.kpis.GrossMarginPct, "%", "margin", "Gross margin"),
    renderMisPrimaryKpi("CashAndBank", dash.kpis.CashAndBank, "INR", "cash", "Cash & bank"),
  ].filter(Boolean).join("");

  const chips = [
    renderMisChip("DSO", dash.kpis.DSO, "days", "DSO"),
    renderMisChip("DPO", dash.kpis.DPO, "days", "DPO"),
    renderMisChip("CurrentRatio", dash.kpis.CurrentRatio, "x", "Current ratio"),
    renderMisChip("CashRunwayMonths", dash.kpis.CashRunwayMonths, "mo", "Cash runway"),
  ].filter(Boolean).join("");

  const summaryParts = [];
  if (dash.pnl.Revenue != null) {
    summaryParts.push(`<div class="mis-summary__item"><span class="mis-summary__label">Total revenue</span><span class="mis-summary__value">${escapeHtml(formatMisMoney(dash.pnl.Revenue))}</span></div>`);
  }
  if (dash.pnl["Gross Profit"] != null) {
    summaryParts.push(`<div class="mis-summary__item"><span class="mis-summary__label">Gross profit</span><span class="mis-summary__value">${escapeHtml(formatMisMoney(dash.pnl["Gross Profit"]))}</span></div>`);
  }
  if (dash.pnl.PAT != null) {
    summaryParts.push(`<div class="mis-summary__item"><span class="mis-summary__label">PAT</span><span class="mis-summary__value">${escapeHtml(formatMisMoney(dash.pnl.PAT))}</span></div>`);
  }

  const hasAgeing = Object.keys(dash.ageing.AR).length || Object.keys(dash.ageing.AP).length;
  const trendPanel = renderMisRevenueTrend(
    [
      ...dash.revenueTrend,
      dash.pnl.Revenue != null
        ? { period: "Current", amount: dash.pnl.Revenue }
        : null,
    ].filter(Boolean),
  );
  const pnlPanel = renderMisPnlTable(dash.pnl);
  const cashPanel = renderMisCashTable(dash.cash);
  const bodyPanels = [
    hasAgeing ? renderMisAgeingColumnChart("AR", dash.ageing.AR) : "",
    hasAgeing ? renderMisAgeingColumnChart("AP", dash.ageing.AP) : "",
    trendPanel,
    pnlPanel,
    cashPanel,
  ].filter(Boolean).join("");

  if (!primary && !chips && !bodyPanels) {
    return `<p class="muted" style="margin-top:0.75rem;">Dashboard widgets appear after KPI / ageing facts are imported.</p>`;
  }

  return `
    <section class="mis-dash" aria-label="Pack dashboard">
      <h5 class="mis-dash__title">Pack dashboard</h5>
      <p class="mis-dash__sub">Derived from imported MIS facts (not AI estimates).</p>
      ${primary ? `<div class="mis-dash__kpi-row">${primary}</div>` : ""}
      ${chips ? `<div class="mis-dash__chip-row">${chips}</div>` : ""}
      ${summaryParts.length ? `<div class="mis-dash__summary">${summaryParts.join("")}</div>` : ""}
      ${bodyPanels ? `<div class="mis-dash__grid">${bodyPanels}</div>` : ""}
    </section>
  `;
}

export function renderMisNarrativeSection(pack) {
  if (!pack) return "";
  const narrative = pack.narrative && typeof pack.narrative === "object" ? pack.narrative : null;
  const bullets = Array.isArray(narrative?.bullets) ? narrative.bullets : [];
  const rows = bullets.map((item) => {
    const ids = Array.isArray(item.fact_ids) ? item.fact_ids : [];
    const cites = ids.map((fid) => {
      const id = String(fid);
      return `<button type="button" class="mis-cite" data-office-ai-action="mis-cite-fact" data-fact-id="${escapeHtml(id)}" title="Show cited fact">${escapeHtml(id)}</button>`;
    }).join(" ");
    return `<li class="mis-narrative__item"><span>${escapeHtml(item.text || "")}</span><span class="mis-narrative__cites">${cites || '<span class="muted">no citation</span>'}</span></li>`;
  }).join("");
  const advisory = escapeHtml(narrative?.advisory || "Draft for review — not final financial advice or a statutory filing.");
  const source = narrative?.source || (narrative?.ai_available ? "ai" : "deterministic");
  const meta = narrative
    ? `Source: ${escapeHtml(source)} · ${escapeHtml(narrative.prompt_version || "")}`
    : "No narrative yet.";
  const frozen = String(pack.status || "").toLowerCase() === "exported";
  return `
    <div class="stack-form mis-narrative" style="margin-top:1rem;">
      <h5>Narrative (cited)</h5>
      <p class="muted">${advisory}</p>
      <button class="secondary" type="button" data-office-ai-action="mis-generate-narrative" ${frozen ? "disabled" : ""}>Generate narrative</button>
      ${frozen ? '<p class="muted">Narrative is frozen after export. Create a new pack revision to regenerate.</p>' : ""}
      <p class="muted">${meta}</p>
      ${rows ? `<ul class="mis-narrative__list">${rows}</ul>` : '<p class="muted">Generate a draft narrative. Every bullet must cite a fact id.</p>'}
    </div>
  `;
}
