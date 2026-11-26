/**
 * Citation Checker — verifies every case citation and criminal-code section
 * in pasted text or an uploaded PDF/DOCX/TXT. Deterministic backend check;
 * no AI generation. Text and files are not stored.
 */

const SEVERITY_ICON = { ok: "✅", info: "🔁", warning: "⚠️", error: "❌" };
const SEVERITY_ORDER = { error: 0, warning: 1, info: 2, ok: 3 };
const KIND_LABEL = { case: "Case", statute: "Section", mapping: "Old → new mapping" };

function escape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function citationToolBodyHtml() {
  return `
    <p class="legal-tool-intake-lead">
      Paste your draft or the other side's written submissions, or upload a PDF / DOCX / TXT.
      LegalMitra checks every <strong>case citation</strong> and every <strong>IPC / CrPC / Evidence Act /
      BNS / BNSS / BSA section</strong>, and flags wrong citations, non-existent sections and wrong
      old → new code mappings. Nothing you paste or upload is stored.
    </p>
    <label>Paste text
      <textarea id="tool-citation-text" rows="8" placeholder="Example: Section 420 IPC (now Section 318(4) BNS)... Reliance is placed on Kesavananda Bharati v. State of Kerala, (1973) 4 SCC 225."></textarea>
    </label>
    <label>Or upload a file (PDF with a text layer, DOCX or TXT)
      <input id="tool-citation-file" type="file" accept=".pdf,.docx,.txt">
    </label>
    <button type="button" data-tool-action="citation-check">Check citations</button>
    <div class="legal-tool-result" id="tool-result">Results appear here. Scanned PDFs without a text layer are not supported yet — paste the text instead.</div>
  `;
}

function safeHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? url.href : "";
  } catch {
    return "";
  }
}

function scRecordHtml(sc) {
  const cites = [sc.neutral_citation, sc.scr_citation].filter(Boolean).map(escape).join("; ");
  const date = sc.decision_date ? `, decided ${escape(sc.decision_date)}` : "";
  const href = safeHttpsUrl(sc.pdf_url);
  const link = href
    ? ` <a href="${escape(href)}" target="_blank" rel="noopener noreferrer">Open judgment (PDF)</a>`
    : "";
  return `Supreme Court: <em>${escape(sc.title)}</em>${cites ? ` — ${cites}` : ""}${date}.${link}`;
}

function itemDetail(item) {
  const parts = [];
  const record = item.matched_record;
  if (record) {
    const alts = (record.alternative_citations || []).slice(0, 3).join("; ");
    parts.push(
      `Our record: <em>${escape(record.title)}</em>${record.citation ? `, ${escape(record.citation)}` : ""}` +
        (alts ? ` <span class="citation-check-muted">(also ${escape(alts)})</span>` : ""),
    );
    for (const note of record.treatment_notes || []) {
      parts.push(`Treatment note: ${escape(note)}`);
    }
  }
  for (const sc of item.supreme_court_matches || []) {
    parts.push(scRecordHtml(sc));
  }
  if (item.library_title) {
    parts.push(`Library document: <em>${escape(item.library_title)}</em>`);
  }
  return parts.map((p) => `<div class="citation-check-detail">${p}</div>`).join("");
}

export function renderCitationCheckResult(payload) {
  const items = [...(payload.items || [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  const s = payload.summary || {};
  if (!items.length) {
    return `<div class="legal-tool-output-card">
      <strong>No case citations or criminal-code sections found.</strong>
      <span class="citation-check-muted">The checker currently covers Indian case citations and IPC, CrPC, Evidence Act, BNS, BNSS and BSA sections.</span>
    </div>`;
  }
  const rows = items
    .map(
      (item) => `
      <li class="citation-check-item citation-check-${escape(item.severity)}">
        <span class="citation-check-icon" aria-hidden="true">${SEVERITY_ICON[item.severity] || "•"}</span>
        <div>
          <div class="citation-check-head"><span class="citation-check-kind">${escape(KIND_LABEL[item.kind] || item.kind)}</span>
            <strong>${escape(item.text)}</strong></div>
          <div>${escape(item.message)}</div>
          ${itemDetail(item)}
        </div>
      </li>`,
    )
    .join("");
  const libraryNote = payload.library_unavailable
    ? `<p class="citation-check-muted">Your library could not be searched this time; only LegalMitra's curated records were used.</p>`
    : "";
  const truncated = payload.truncated
    ? `<p class="legal-tool-disclaimer">Only the first part of a very long document was checked.</p>`
    : "";
  return `
    <div class="legal-tool-output-card">
      ${payload.file_name ? `<span class="citation-check-muted">File: ${escape(payload.file_name)}</span>` : ""}
      <div class="citation-check-summary">
        <span>❌ ${Number(s.error || 0)} problems</span>
        <span>⚠️ ${Number(s.warning || 0)} to verify</span>
        <span>🔁 ${Number(s.info || 0)} old-code sections</span>
        <span>✅ ${Number(s.ok || 0)} verified</span>
      </div>
      ${truncated}
      <ul class="citation-check-list">${rows}</ul>
      ${libraryNote}
      <p class="legal-tool-disclaimer">${escape(payload.advisory || "")}</p>
      ${payload.attribution ? `<p class="citation-check-muted">${escape(payload.attribution)}</p>` : ""}
    </div>`;
}

/** Run the check. `request(path, options)` is the app's authenticated API call. */
export async function runCitationCheck(request) {
  const text = (document.getElementById("tool-citation-text")?.value || "").trim();
  const file = document.getElementById("tool-citation-file")?.files?.[0];
  if (!file && text.length < 3) {
    return { html: "Paste some text or choose a file first." };
  }
  let result;
  if (file) {
    const form = new FormData();
    form.append("file", file);
    result = await request("/api/v1/legalmitra/citation-check/upload", {
      method: "POST",
      body: form,
      timeoutMs: 60000,
    });
  } else {
    result = await request("/api/v1/legalmitra/citation-check", {
      method: "POST",
      body: JSON.stringify({ text }),
      timeoutMs: 60000,
    });
  }
  if (result.status === 401) {
    return { html: `<span class="legal-tool-missing">Please sign in to use the Citation Checker.</span>` };
  }
  if (!result.ok) {
    const detail = result.payload?.detail || "The citation check could not be completed. Please try again.";
    return { html: `<span class="legal-tool-missing">${escape(typeof detail === "string" ? detail : "Request failed.")}</span>` };
  }
  return { html: renderCitationCheckResult(result.payload || {}) };
}

/* ── Supreme Court Judgment Finder ─────────────────────────────────────── */

export function judgmentFinderBodyHtml() {
  return `
    <p class="legal-tool-intake-lead">
      Find any <strong>Supreme Court of India</strong> judgment since 1950 by party names, neutral citation
      (e.g. <em>2021 INSC 469</em>) or SCR citation, and open the full judgment PDF.
      SCC / AIR citations are not in this open dataset.
    </p>
    <label>Party names or citation
      <input id="tool-judgment-query" placeholder="Example: Arnesh Kumar v. State of Bihar">
    </label>
    <label>Year (optional)
      <input id="tool-judgment-year" type="number" min="1950" max="2100" placeholder="Example: 2014">
    </label>
    <button type="button" data-tool-action="judgment-finder">Find judgment</button>
    <div class="legal-tool-result" id="tool-result">Results appear here with a link to the full judgment.</div>
  `;
}

export async function runJudgmentFinder(request) {
  const q = (document.getElementById("tool-judgment-query")?.value || "").trim();
  const year = (document.getElementById("tool-judgment-year")?.value || "").trim();
  if (q.length < 2) {
    return { html: "Enter party names or a citation first." };
  }
  const params = new URLSearchParams({ q });
  if (/^\d{4}$/.test(year)) params.set("year", year);
  const result = await request(`/api/v1/legalmitra/judgments/search?${params.toString()}`, {
    method: "GET",
    timeoutMs: 30000,
  });
  if (result.status === 401) {
    return { html: `<span class="legal-tool-missing">Please sign in to use the Judgment Finder.</span>` };
  }
  if (!result.ok) {
    return { html: `<span class="legal-tool-missing">Search failed. Please try again.</span>` };
  }
  const payload = result.payload || {};
  const rows = (payload.results || [])
    .map(
      (sc) => `<li class="citation-check-item citation-check-ok">
        <span class="citation-check-icon" aria-hidden="true">⚖️</span>
        <div>
          <div>${scRecordHtml(sc)}</div>
          ${sc.bench ? `<div class="citation-check-detail">Bench: ${escape(sc.bench)}</div>` : ""}
          ${sc.disposal ? `<div class="citation-check-detail">Outcome: ${escape(sc.disposal)}</div>` : ""}
        </div>
      </li>`,
    )
    .join("");
  const body = rows
    ? `<ul class="citation-check-list">${rows}</ul>`
    : `<strong>No Supreme Court judgment found.</strong> <span class="citation-check-muted">Try fewer words, a different spelling, or the year. High Court judgments are not included yet.</span>`;
  return {
    html: `<div class="legal-tool-output-card">${body}
      <p class="citation-check-muted">${escape(payload.attribution || "")}</p></div>`,
  };
}
