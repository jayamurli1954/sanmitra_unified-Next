# MitraBooks — AI Finance Agents Roadmap

> Scoping note, 2026-10-22. Triggered by the "50+ AI Finance Agents / Claude Fable 5"
> social graphic. This maps that list against what MitraBooks already is, and scopes
> the first build (Cash Flow Forecast + Runway).

---

## 1. Reality check on the graphic

The "50+ AI Finance Agents" image is a **LinkedIn-style marketing graphic** ("comment
AGENTS + follow + repost"), not a shippable Anthropic product. There is no installable
pack of 50 finance agents that comes out of "Fable 5". What is real:

- **Most of those 50 are not 50 products.** They are thin **AI-analysis layers over the
  same ledger data** — the same trial balance, GL, invoices and aging feeding different
  prompts ("forecast revenue", "find cost reductions", "write the board summary").
  Build the data plumbing once and most of the list becomes prompt + report variations.
- **MitraBooks already runs this exact pattern.** `financial_health.py` is the live
  reference implementation of the **compute → (narrate) → visualize** pipeline: figures
  are computed deterministically from the posted ledger, and Claude only rewrites prose,
  never invents numbers. `ANTHROPIC_API_KEY` is already wired on Render.

So the real question is not "port 50 tools." It is "which of these analysis agents are
worth wiring onto the engine we already have — and which are scope creep."

### The non-negotiable guardrail (from `financial_health.py`)

> *Every figure is computed deterministically from the posted ledger; the LLM only
> rewrites prose.* Any new "agent" MUST follow this. No agent is allowed to produce a
> number an auditor can't trace to the GL.

---

## 2. The 50, mapped against MitraBooks

Legend: **Built** = live today · **Next** = good fit, data already exists · **Later** =
fits but needs new data/engine · **Skip** = wrong product (belongs in an IB/wealth tool,
or is regulated advice).

| # | Agent | Status | Notes / data source |
|---|---|---|---|
| 1 | Financial Modeling | Later | Needs a scenario/driver model layer |
| 2 | Budget Planning | Next | Budget vs GL actuals; no budget store yet (small) |
| 3 | **Cash Flow Forecast** | **Next (first build)** | `ar_ap_aging` + dashboard — see §3 |
| 4 | Revenue Forecasting | Next | 6-month trend in `get_business_dashboard` |
| 5 | Expense Analysis | Next | GL by expense account + narration |
| 6 | Variance Analysis | Next | Period-over-period / budget vs actual on GL |
| 7 | Profitability Analyst | Next | P&L + cost-centre add-on (in build) |
| 8 | Pricing Strategy | Skip | Not an accounting job |
| 9 | Scenario Planning | Later | Depends on #1 model layer |
| 10 | Break-Even | Next | Cost-centre fixed/variable split |
| 11 | FP&A Reporting | **Built** | AI narrative |
| 12 | Management Reporting | **Built** | AI narrative / MIS narrative router |
| 13 | KPI Dashboard | **Built** | Financial Health (live) |
| 14 | Monthly Close | **Built** | Year-end close + period locks |
| 15 | Board Pack Builder | Next | Compose existing reports into one export |
| 16 | Investor Update | Next | Same engine as #15 |
| 17 | **Runway Calculator** | **Next (first build)** | Trivial on top of #3 — see §3 |
| 18 | Burn Rate Monitor | **Next (first build)** | Falls out of #3/#17 |
| 19 | Working Capital | Next | AR + AP + inventory already present |
| 20 | Accounts Receivable | **Built** | Aging + payment allocation |
| 21 | Accounts Payable | **Built** | Aging + payment allocation |
| 22 | Payroll Planning | **Built** | HR/Payroll add-on |
| 23 | Treasury Forecast | Later | Overlaps #3; multi-bank cash positioning |
| 24 | Debt Schedule | Later | Needs a loan/EMI schedule store |
| 25 | Capital Allocation | Skip | CFO-strategy, not SMB accounting |
| 26 | Cost Reduction | Next | Expense GL + cost-centre; narration |
| 27 | Unit Economics | Next | Cost-centre / manufacturing add-on |
| 28 | SaaS Metrics | Skip | Not the SMB/CA segment |
| 29 | Cohort Revenue | Skip | Needs product analytics, not a ledger |
| 30 | Churn Impact | Skip | Not an accounting job |
| 31 | M&A Screening | Skip | IB tool |
| 32 | Due Diligence | Skip | IB tool |
| 33 | Valuation | Skip | IB/wealth tool (we disabled InvestMitra for this reason) |
| 34 | Fundraising Materials | Skip | IB tool |
| 35 | Business Case Builder | Skip | Strategy, not books |
| 36 | Sensitivity Analysis | Later | Depends on #1 |
| 37 | Risk Assessment | Next | Data-health + aging + GST compliance signals |
| 38 | Internal Controls | **Built (partial)** | Period locks, dimensions, audit trail |
| 39 | Audit Prep | **Built (partial)** | Year-end close, GL export, Tally XML |
| 40 | Tax Planning | Later | GST suite exists; income-tax planning is new |
| 41 | Compliance Review | **Built** | GST returns suite (GSTR-1/3B/2B/4, CMP-08) |
| 42 | Procurement Savings | Skip | Not an accounting job |
| 43 | Vendor Spend Analyst | Next | AP party-wise spend + narration |
| 44 | Inventory Finance | **Built** | Inventory add-on (opt-in) |
| 45 | Pricing Margin | Next | Sales + cost-centre margin |
| 46 | Forecast Accuracy | Later | Needs forecast history to score against |
| 47 | Strategic Finance Partner | Skip | Marketing label, not a feature |
| 48 | Investor Relations | Skip | Overlaps #16; not core |
| 49 | Finance Ops Optimizer | Skip | Vague marketing label |
| 50 | CFO Decision Support | Partial | = Financial Health + narration, already live |

### Tally

- **Built / partial: ~14** (11–14, 20–22, 38–39, 41, 44, 50 + partials)
- **Worth building (Next): ~15** — all are compute-over-existing-ledger + narration
- **Skip (wrong product / regulated): ~13**
- **Later (needs a new engine — mainly a driver/scenario model): ~8**

### The cluster worth doing first

**#3 Cash Flow Forecast + #17 Runway + #18 Burn Rate** are one build. They share inputs,
they're the highest-demand asks from SMBs and startup clients, and every input already
exists. Scoped in §3.

Natural follow-on cluster (same template, cheap once #3 ships): **#5 Expense Analysis,
#6 Variance, #43 Vendor Spend** — all are "GL slice + Claude narration".

---

## 3. First build — Cash Flow Forecast + Runway + Burn Rate

### Why this one

Highest value, lowest risk. It is a **near-clone of `financial_health.py`** — same
`assemble` / `build` / `narrate` shape, same trusted inputs, same guardrail. No new data
model, no migration.

### Inputs (all already exist)

| Input | Source | Gives us |
|---|---|---|
| Opening cash | `get_business_dashboard` → as-of cash balance | Forecast start position |
| Expected inflows | `allocation_service.ar_ap_aging(kind="receivable")` | Receivables by age bucket → timing of collections |
| Expected outflows | `allocation_service.ar_ap_aging(kind="payable")` | Payables by age bucket → timing of payments |
| Run-rate / burn | `get_business_dashboard` → FYTD P&L + 6-month income-vs-expense trend | Monthly operating burn |
| Annualising constant | `financial_health._DAYS_PER_MONTH = 30.44` | FYTD → monthly run-rate |

### Method (deterministic, auditable)

1. **Burn rate** = (FYTD operating outflow − FYTD operating inflow) / months elapsed,
   from the dashboard trend. Report gross burn and net burn separately.
2. **Projected cash, month N** = opening cash
   + scheduled AR collections landing in month N (from aging buckets → due windows)
   − scheduled AP payments due in month N
   − projected operating burn for month N.
   Project a fixed horizon (default 6 months; param `horizon_months`).
3. **Runway** = months until projected cash crosses zero (∞ / "cash-positive" when burn
   is non-positive). Report as "X.Y months" + the projected zero-crossing date.
4. **Alerts** (deterministic, same shape as Financial Health): runway < 3 months = bad;
   < 6 = warn; large payable cliff in a single month; collections concentrated in 90+.
5. **Narration** (optional): Claude rewrites the summary into CFO prose. Gated, graceful
   fallback to the deterministic summary. Never touches a number.

### Files to add / touch

| File | Change |
|---|---|
| `app/modules/business/cash_flow_forecast.py` | **New.** `assemble_cash_flow_forecast(...)` (pure), `build_cash_flow_forecast(...)` (async gatherer), `narrate_cash_flow_forecast(...)` (Claude, gated). Mirror `financial_health.py` 1:1. |
| `app/modules/business/routes/reports.py` | **New endpoint** `@router.get("/cash-flow-forecast")` beside `/financial-health` (L62). Reuse `_alloc_context(...)` for tenant isolation. Query params: `as_of`, `horizon_months`, `narrate`. |
| `app/config.py` | Settings flags mirroring the FH ones: `CASH_FLOW_AI_ENABLED`, `CASH_FLOW_AI_MODEL`, `CASH_FLOW_AI_MAX_TOKENS` (or reuse the FH flags if we want one switch). |
| `frontend/.../app.js` (business reports workspace) | New tab in `BUSINESS_REPORT_TABS` → "Cash Flow Forecast". Line chart of projected balance + runway headline + alerts. Reuse the Financial Health render path (data-attribute delegation, no inline onclick). |
| `tests/test_cash_flow_forecast.py` | **New.** Unit-test `assemble_*` as a pure function over synthetic dashboard + aging dicts (copy the shape from `tests/test_financial_health.py`). Cover: positive cash, burn with finite runway, zero-crossing date, payable-cliff alert, empty ledger. |

### Guardrails specific to this build

- **Tenant isolation** via `_alloc_context` on the endpoint — same as every business report.
  Never query across tenants; the aging/dashboard helpers already scope by
  `tenant_id` + `app_key` + `accounting_entity_id`.
- **No LLM numbers.** The narration prompt receives an already-computed snapshot and is
  told to write prose only — copy `financial_health.build_narration_prompt` exactly.
- **Graceful degrade.** If `ANTHROPIC_API_KEY` is unset or the call fails, return the
  deterministic summary (narration = None). Matches FH behaviour; no user-visible error.
- **Aging → timing assumption must be stated.** Buckets are *days past due*, not future
  due dates. v1 maps "0-30 current" → expected within the month and overdue buckets →
  expected immediately, and **labels this assumption in the response** so it isn't read
  as a precise AP/AR schedule. A later slice can use real invoice due dates for exact
  timing.

### Effort

~1 focused build. Backend module + endpoint + settings ≈ half; one frontend tab ≈ a
quarter; tests ≈ a quarter. No migration, no new dependency. Ship behind the existing
opt-in reports workspace, same as Financial Health.

### Explicitly out of scope for v1

- Exact invoice-due-date timing (v1 uses aging buckets — see assumption above).
- Multi-bank treasury positioning (#23).
- Scenario sliders (#9/#36) — those need the driver-model layer that doesn't exist yet.
- Forecast-accuracy scoring (#46) — needs stored forecast history to compare against.

---

## 4. Suggested sequence after the first build

1. **Cash Flow Forecast + Runway + Burn** (§3) — this build.
2. **Expense Analysis + Variance + Vendor Spend** (#5, #6, #43) — same template, GL slices.
3. **Board Pack / Investor Update** (#15, #16) — composition of existing reports, one export.
4. Revisit the driver-model layer only if customers ask for true scenario planning (#1/#9/#36).

Everything in the **Skip** column stays out of MitraBooks — it belongs to an investment
or IB product, or is regulated advice. Building it here repeats the InvestMitra mistake.
