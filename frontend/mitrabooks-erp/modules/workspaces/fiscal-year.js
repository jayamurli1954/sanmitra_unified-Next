// ====================================================================
// SECTION: INDIAN FINANCIAL YEAR HELPERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. No shell deps (pure date helpers).
// ====================================================================

// Current Indian financial year as "YYYY-YY" (FY starts April).
// Current Indian-FY quarter as "YYYY-Q[1-4]" (FY starts April; Q1 = Apr-Jun).
// A handful of recent FY quarters for the CMP-08 picker.

export function currentFinancialYear() {
  const d = new Date();
  const startYear = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
  return `${startYear}-${String(startYear + 1).slice(-2)}`;
}

export function recentFinancialYears(count = 4) {
  let startYear = Number(currentFinancialYear().slice(0, 4));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${startYear}-${String(startYear + 1).slice(-2)}`);
    startYear -= 1;
  }
  return out;
}

export function currentFyQuarter() {
  const d = new Date();
  const m = d.getMonth(); // 0-11
  const y = d.getFullYear();
  if (m >= 3 && m <= 5) return `${y}-Q1`;
  if (m >= 6 && m <= 8) return `${y}-Q2`;
  if (m >= 9 && m <= 11) return `${y}-Q3`;
  return `${y - 1}-Q4`;       // Jan-Mar belongs to the FY that started the prior April
}

export function recentFyQuarters(count = 6) {
  const cur = currentFyQuarter();
  let [fy, q] = cur.split("-Q").map((x, i) => (i === 0 ? Number(x) : Number(x)));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${fy}-Q${q}`);
    q -= 1;
    if (q < 1) { q = 4; fy -= 1; }
  }
  return out;
}

export function financialYearStartIso() {
  const now = new Date();
  // Indian financial year starts April 1. Jan-Mar (month index 0-2) belong to the prior FY.
  const year = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  return `${year}-04-01`;
}

