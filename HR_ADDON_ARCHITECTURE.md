# HR / Payroll Add-On — Architecture Sketch (Sanmitra-native)

**Status:** Steps 1–8 **built** on branch `feat/hr-addon-foundation` — see Build Log §12. v1 feature-
complete (53 HR tests green).
**Date:** 2026-06-22
**Inputs:** Gemini design note (`HR_Module.docx`, reference for Indian rules only) + Frappe HR
domain model (ideas borrowed, not cloned).

---

## 1. Guiding principles

1. **Opt-in add-on, not a core feature.** Provisioned per tenant only when a client buys it —
   same gate pattern as `inventory_enabled` on `InvoiceSettings` today. Tenants without it carry
   zero schema, route, or UI weight.
2. **Borrow ideas, build our own way.** Take the *proven concepts* from Frappe HR (configurable
   salary structure, leave ledger, payroll batch, tax-slabs-as-data). Drop the Frappe-isms
   (DocTypes, metadata engine, naming series, client scripts). Express everything in our own
   Pydantic + Mongo idiom.
3. **Reuse existing core, don't reinvent.** We already have audit, permissions, documents (PDF),
   tenant isolation, and a double-entry accounting engine. The add-on plugs into all of them.
4. **Lean to what Indian SMBs on MitraBooks actually need.** Not a 13-module ERP HR suite.
5. **No code copied** from the Gemini doc (it targets Django/SQL/S3 and has bugs) or from Frappe
   (wrong stack). Both are reference inputs; the output is original.

---

## 2. Where it lives

```
app/modules/hr/                  # new isolated module, mirrors app/modules/business/
├── __init__.py
├── router.py                    # /hr/* routes, registered only when tenant flag is on
├── schemas.py                   # Pydantic models (Employee, SalaryStructure, ...)
├── service.py                   # business logic
├── payroll_engine.py            # PURE statutory math (no DB) — EPF/ESIC/PT/TDS/gratuity
├── leave_ledger.py              # immutable leave credit/debit rows
├── payroll_run.py               # batch run over employees -> slips -> GL posting
├── tax_declaration.py           # Form 12BB lifecycle (declare -> proof -> approve)
├── fnf.py                       # Full & Final settlement
├── documents.py                 # maps HR records -> core DocumentSpec (slip / letter / F&F)
└── seed.py                      # statutory config seed (slabs, PT tables, leave types)
```

**Reused core (no new copies):**
- `app/core/permissions/rbac.py` — add HR roles (see §7).
- `app/core/audit/service.py` — all sensitive reads/writes log here. **Do not** build a new audit system.
- `app/core/documents/` — salary slips, appointment letters, F&F vouchers render through the
  existing `DocumentSpec` + renderer you just shipped.
- `app/accounting` (`post_journal_entry` / `reverse_journal_entry`) — payroll posts to the GL.
- File uploads (tax proofs) — stored **as bytes in Mongo**, the CA-file-upload pattern, **not S3**.

---

## 3. Feature flag & provisioning  *(decision: inside MitraBooks, platform-owner gated)*

HR is a **full-enterprise feature inside MitraBooks**, not a separate app. It is gated at two levels:

1. **Platform-owner switch** — only the platform owner can turn the HR capability *available* for a
   tenant (the enterprise/paid tier). This lives with the existing platform-owner controls
   (`app/core/platform_owner/`), not in the tenant's own settings — a tenant cannot self-enable it.
2. **Tenant on/off** — once the platform owner has made it available, an `hr_enabled: bool = False`
   flag on MitraBooks `InvoiceSettings` (alongside `inventory_enabled`) lets the tenant admin turn
   the module on/off in their own settings.

- `router.py` routes are guarded so a tenant without **both** flags gets 404/disabled, mirroring the
  InvestMitra runtime-disable approach.
- Sidebar entries render conditionally (the established opt-in pattern).
- Collections are created lazily on first use — no schema bloat for non-HR tenants.

---

## 4. Data model (borrowed concepts, our shapes)

All stored in Mongo, scoped by `tenant_id` from JWT (never from request body). Money as integer
paise or `Decimal` — match whatever the accounting module already uses.

### 4.1 Employee profile
`hr_employee` — links to core user by `user_id`; PAN/UAN/IFSC with regex validators; bank details;
PF/ESIC eligibility flags; PT state. **Aadhaar: deliberately optional / out of v1** — storing it
triggers UIDAI obligations and payroll doesn't need it (PAN + UAN suffice). Revisit only if a real
requirement appears.

### 4.2 Salary structure (the Frappe idea worth stealing)
Instead of hardcoding "Basic = 50%", a structure is a list of **components**, each a row:

```
SalaryComponent { name, type: earning|deduction, formula, condition, taxable, statutory_kind }
```

- `formula` / `condition` are evaluated per employee against a small, sandboxed variable set
  (`ctc`, `basic`, `gross`, `lop_days`, ...). This solves the CTC-vs-gross ambiguity the Gemini
  doc never resolved: the tenant *declares* the relationship.
- Ship sensible **preset structures** (metro / non-metro) so SMBs don't start from scratch — but
  they remain editable data, not code.
- `statutory_kind` ∈ {basic, hra, epf_ee, epf_er, esic_ee, esic_er, pt, tds, ...} so the engine and
  GL posting know which legal head each component maps to.

### 4.3 Statutory config as data (not `if` statements)
- `hr_income_tax_slab` — brackets + rate + cess, versioned by FY and regime (old/new). A Union
  Budget change is a **data edit**, not a deploy.
- `hr_pt_slab` — state-wise professional-tax tables.
- Constants (EPF 12% / ₹15,000 ceiling, ESIC 0.75%/3.25% @ ₹21,000, gratuity ₹20L cap, §10(10AA)
  ₹25L) live in a single versioned config doc.

### 4.4 Leave (ledger, not a counter)
- `hr_leave_type`, `hr_leave_policy` (type → grade allocation).
- **`hr_leave_ledger`** — every credit/debit is an immutable row (the Frappe Leave Ledger idea).
  Balance = sum of rows. Far more auditable than the Gemini doc's mutable `paid_leave_available`,
  and it naturally supports carry-forward caps and encashment.

### 4.5 Payroll
- `hr_salary_slip` — per employee per month; component breakdown; payable days; LOP; net;
  `journal_entry_id` link to the posted GL entry.
- `hr_payroll_run` — the batch header (the Frappe "Payroll Entry"): one run over all active
  employees for a month, produces slips, posts one consolidated journal.

### 4.6 Tax declaration (Form 12BB)
- `hr_tax_declaration` (declared vs verified amounts, status machine
  DECLARED→SUBMITTED→APPROVED/REJECTED) + proof file bytes in Mongo.
- Three-phase cycle: **April declare → Jan proof upload → Feb/Mar HR verify** (both reference docs
  agree here; it's correct).

### 4.7 Full & Final
- `hr_fnf` — gratuity `(last_basic × 15 × years)/26` capped ₹20L; leave encashment
  `(last_basic/30) × unused`; notice recovery; asset-clearance hook into your asset module.

---

## 4b. LOP — derived, never typed  *(borrowed from Frappe HR `salary_slip.py`)*

**Decision: HR never hand-enters an LOP number** (error-prone). LOP is *computed* by the system as a
byproduct of two upstream sources of truth, exactly as Frappe does it. I read their real code
(`hrms/payroll/doctype/salary_slip/salary_slip.py`, `get_working_days_details` +
`calculate_lwp_*`). The idea we borrow (not the code):

**The formula:**
```
payment_days = total_working_days − holidays − lwp − absent_days
```
where `total_working_days` comes from a **Holiday List** (weekends/festivals excluded), and `lwp`
(leave-without-pay) / `absent_days` are *derived*, never entered.

**Two configurable derivation modes** (a `payroll_based_on` setting, per Frappe):

1. **Leave-Application mode** *(cleanest v1, no attendance hardware needed):*
   LOP is computed by walking each working day in the period and checking approved **leave
   applications**. Only leave types flagged `is_lwp` (unpaid) or `is_ppl` (partially paid) reduce
   pay. Paid leave (CL/EL/SL *with balance*) does **not** cause LOP. When an employee exhausts paid
   balance, the excess leave is recorded against an unpaid type → automatic LOP. Half-days count
   fractionally. **HR types nothing — LOP falls out of the approved-leave workflow.**

2. **Attendance mode** *(more accurate, needs a daily-presence feed):*
   LOP + absent days are derived from per-day **attendance records** (status Absent / Half-Day /
   On-Leave). A key setting, `consider_unmarked_attendance_as` (Present | Absent), makes missing
   marks deterministic instead of ambiguous.

**v1 scope — leave-driven LOP only (decided: start simple).** v1 uses **Leave-Application mode**
exclusively:

- LOP is computed by walking the working days (Holiday List excluded) and checking approved
  **leave applications**. Paid leave with balance → no LOP. Unpaid leave types, or paid leave that
  **overflows the available balance**, → automatic LOP. Half-days fractional.
- Needs only the leave module we're building anyway — **zero new infrastructure**, and it already
  removes manual LOP entry (the user's hard requirement).
- **Known limitation, accepted for v1:** a *silent no-show* who never files leave is **not** caught,
  because there's no daily presence record to contradict them. This is a conscious trade for
  simplicity, not an oversight.

**Deferred to a later phase — self-service check-in (Attendance mode).** When stricter capture is
wanted, add a lightweight **employee Check-in/Check-out** (web/PWA, optional geo/IP), a nightly
**auto-attendance** job that rolls check-ins into daily `hr_attendance` rows, and the
`consider_unmarked_attendance_as` (Present | Absent) toggle so a day with neither check-in nor
approved leave becomes deterministic LOP. The check-in event model is forward-compatible with
biometric/geo hardware later. **Not in v1.** The payroll engine's `payroll_based_on` switch is
designed in from the start so flipping to Attendance mode later is config, not a rewrite.

Net: in v1, LOP is a **calculated output** of approved-leave data, never a number an HR admin can
fat-finger. The leave **ledger** (§4.4), the Holiday List, and these derivation rules are the
guardrails — with presence-based capture as a clean later upgrade.

---

## 5. The payroll engine (pure, testable)

`payroll_engine.py` is a **pure library**: inputs → dict, no DB, no I/O. This is the one place the
Gemini doc had the right instinct (isolate the math) but the wrong execution (buggy, incomplete).
Our version:

- Computes Basic/HRA/special from the **salary structure formulas**, not hardcoded 50/40.
- EPF on `min(basic, 15000)`; ESIC only if gross ≤ 21,000; PT from state slab; TDS on **taxable
  income after deductions**, both regimes, slab-driven, cess applied.
- LOP pro-ration drives *paid days*, and EPF naturally scales because it's computed on adjusted
  basic.
- 100% unit-testable headless (the repo's testing norm) — golden cases per statutory rule.

---

## 6. Accounting integration (the piece both docs miss)

This is what makes it a real ERP feature, not a standalone calculator. A payroll run posts to the
existing ledger via `post_journal_entry`, the **same path invoices/vouchers use** today
(`service.py` posts then stores `journal_entry_id`):

```
Dr  Salaries & Wages (expense)        gross earnings
    Cr  EPF Payable (employee+employer)
    Cr  ESIC Payable
    Cr  Professional Tax Payable
    Cr  TDS Payable
    Cr  Salaries Payable (net)         -> cleared on bank disbursal
```

- Reversal uses `reverse_journal_entry` (same as voucher/invoice cancel).
- Statutory payables become real liabilities visible in BS / aging / GST-adjacent reports you
  already built.
- F&F and bonuses post the same way.

---

## 7. Security, roles, audit

- **Roles** (add to `Role` enum, reuse `require_roles`): `hr_manager`, `payroll_auditor`,
  `employee_self`. Existing `tenant_admin` does **not** get payroll visibility by default — must be
  explicitly granted (sensitive comp data).
- **Audit**: every read of bank/PAN/salary and every write routes through `app/core/audit` — no new
  audit subsystem. Mask sensitive fields in log payloads.
- **Tenant isolation**: `tenant_id` from JWT only, enforced by the existing dependency — same
  invariant proven by the isolation-matrix tests.

---

## 8. Documents

Appointment letter, monthly salary slip, and F&F statement all map an HR record → `DocumentSpec` →
existing renderer. Multilingual support comes for free from the layer you just built (useful for
regional salary slips). No new PDF engine.

---

## 9. Suggested build order (each independently shippable, flag-gated)

1. **Foundation** — module skeleton, `hr_enabled` flag, Employee profile + roles + audit wiring.
2. **Salary structure + payroll engine** (pure math + unit tests). No DB writes yet.
3. **Payroll run + GL posting** — batch → slips → journal entry. The core value.
4. **Leave ledger + LOP** feeding the run.
5. **Form 12BB** declaration/proof/verify + TDS reconciliation.
6. **F&F settlement** + gratuity/encashment + asset hook.
7. **Salary-slip / appointment-letter / F&F PDFs** via documents layer.
8. **Analytics** (cached monthly summary) — last, lowest priority.

Audit is wired in from step 1, not bolted on at the end.

---

## 10. Explicitly out of scope for v1

Aadhaar vault; recruitment/ATS; performance reviews; shift/roster planning; **self-service
check-in / Attendance-mode LOP** (deferred phase — see §4b); biometric attendance hardware; the full
Frappe 13-module suite. Add-on stays lean to what's asked for.

---

## 11. Decisions

**Settled:**
- ✅ **Home:** inside MitraBooks as an enterprise feature, **platform-owner gated** + tenant on/off
  flag (§3).
- ✅ **LOP:** system-derived, never manually typed — Frappe-style leave/attendance derivation (§4b).
- ✅ **Frappe source:** cloned to `external-repos/frappe-hrms`; design now grounded in the real
  `salary_slip.py` logic, not memory. Ideas borrowed, no code copied.

- ✅ **LOP scope v1:** leave-driven only — start simple. Self-service check-in / Attendance-mode
  LOP is **deferred to a later phase** (silent no-shows uncaught in v1, accepted). The
  `payroll_based_on` switch is built in so the upgrade is config, not a rewrite (§4b).

**Still open:**
1. **Money type:** confirm paise-int vs `Decimal` to match the accounting module exactly.

---

## 12. Build Log — Step 1 Foundation (`feat/hr-addon-foundation`)

Shipped:
- **Module** `app/modules/hr/`: `schemas.py` (Employee profile + PAN/UAN/IFSC validators, Aadhaar
  out of v1), `service.py` (Employee CRUD on `hr_employees`, tenant-scoped, audit-logged with
  sensitive-field redaction), `gating.py` (two-level gate), `router.py`.
- **Two-level gate**: platform owner sets `core_tenants.hr_addon_available` via new
  `PUT /api/v1/platform-owner/tenants/{id}/hr-addon` (super_admin only); tenant admin sets
  `InvoiceSettings.hr_enabled` via the existing invoice-settings PUT.
- **Roles** added to `app/core/permissions/rbac.py`: `hr_manager`, `payroll_auditor`,
  `employee_self`.
- **Wiring**: router in `app/api/v1/router.py`; `ensure_hr_indexes()` in `app/main.py` startup.
- **Tests**: `tests/test_hr_foundation.py` — 10 tests (validators, CRUD, duplicate guard, tenant
  isolation, audit redaction, both gate levels). All green; touched suites (business contract,
  composition, tenant policy, CA access, route-contract) still green.

Two implementation notes worth flagging:
- **Route prefix is `/business/hr`, not `/hr`.** The unprefixed `mandir_compat` router already
  serves global stub `GET /hr/employees` + `/hr/attendance/monthly`; nesting under `/business/hr`
  avoids shadowing and reflects HR-inside-MitraBooks.
- **Fixed a latent `inventory_enabled` bug.** `get_invoice_settings` whitelisted only 4 keys and
  `save_invoice_settings` rebuilt the model from those 4, so `inventory_enabled` (and now
  `hr_enabled`) were silently dropped on every settings save/read. Threaded both flags through both
  functions — inventory toggling via Invoice Settings now actually persists.

### Step 2 — Salary structure + pure payroll engine
- `payroll_engine.py`: pure, DB-free Indian statutory math. Money is `Decimal` (matches the ledger;
  **money-type question resolved → Decimal**). Configurable salary-structure components with
  AST-sandboxed formulas (numeric literals promoted to Decimal; node-type whitelist) solve
  "Basic = 50% of what". Statutory functions: EPF (12% of basic capped ₹15k), ESI (0.75/3.25% under
  ₹21k gross), professional tax (state slab tables as data), income tax (new+old regimes as slab
  data, std deduction, 87A rebate, new-regime marginal relief, 4% cess), gratuity ((Basic×15×yrs)/26
  capped ₹20L). `compute_payroll` orchestrates one employee/month with LOP proration.
- Tests `tests/test_hr_payroll_engine.py` (13) — all against authoritative figures.

### Step 3 — Payroll run + GL posting
- `payroll_run.py`: batch over active employees with a salary assignment → salary slips → **one
  consolidated journal entry** via `post_journal_entry` (same path as invoices/vouchers), idempotent
  per period. Dr Salaries&Wages + Employer cost; Cr EPF/ESI/PT/TDS payables + Salaries Payable.
- New COA accounts added to `DEFAULT_BUSINESS_CHART_OF_ACCOUNTS` (idempotent init provisions them
  for existing tenants): `21003` Salaries Payable, `23005` EPF, `23006` ESI, `23007` PT, `23008` TDS
  (Salary), `52002` Employer Statutory Contributions.
- Salary structure CRUD + per-employee salary assignment (one active). Tests
  `tests/test_hr_payroll_run.py` (4) incl. a balanced-journal assertion (Dr=Cr=₹146,465).

### Step 4 — Leave ledger + leave-driven LOP
- `leave.py`: leave types (with `is_lwp` flag), an **immutable leave ledger** (balance = Σ deltas),
  and leave applications whose **approval derives LOP** — paid leave covered by balance, overflow or
  LWP types become LOP. `resolve_lop_days` sums approved-leave LOP for a period and feeds the payroll
  run (the Step 3 `_resolve_lop_days` seam now delegates here). v1 constraint: an application stays
  within one calendar month. Tests `tests/test_hr_leave.py` (9) incl. an integration test proving LOP
  reduces pay in a real run.

**Money type decided: `Decimal`** (matches accounting). The one remaining open item from §11 is now
closed. Full HR suite: 36 tests green; broad regression (business/accounting/COA/tenant/platform):
324 green.

### Step 5 — Form 12BB (tax declarations)
- `tax.py`: declaration lifecycle DECLARED→SUBMITTED→APPROVED/REJECTED; section caps as data
  (`SECTION_LIMITS`, None = uncapped); **proof files stored as bytes in Mongo** (10 MB cap +
  PDF/JPEG/PNG allowlist, never leaked through serializers). `compute_effective_deductions` sums
  approved verified amounts per section, capped, → old-regime Chapter VI-A total. Wired into the
  run via `_resolve_chapter_deductions` seam (FY derived from period; prefers verified declarations,
  falls back to the assignment estimate). Tests `tests/test_hr_tax.py` (7), incl. old-regime TDS
  using verified 80C.

### Step 6 — Full & Final settlement
- `fnf.py` + engine `compute_fnf`/`compute_leave_encashment`/`compute_notice_recovery`: tenure
  computed from DOJ→last-working-day (gratuity eligibility/years not hand-typed); gratuity
  (₹20L cap), leave encashment (Basic/30 × unused), notice recovery; status machine
  draft→approved→paid; paying it exits the employee. GL posting of the settlement deferred (same
  pattern as the run). Tests `tests/test_hr_fnf.py` (5).

### Step 7 — PDFs (shared documents layer)
- `documents.py`: maps salary slips and F&F statements into the existing `app/core/documents`
  `DocumentSpec` renderer (no new PDF engine; ₹ glyph supported). Download endpoints
  `GET …/payroll/slips/{id}/pdf` and `…/fnf/{id}/pdf`. Tests `tests/test_hr_documents.py` (3) render
  valid PDF bytes. Appointment letter (prose, not line-item) deferred — the shared layer is
  line-item/totals shaped.

### Step 8 — Analytics
- `analytics.py`: trailing-N-month dashboard built from the run totals already stored per period
  (no separate cache needed) + current active/exited headcount. Endpoint
  `GET …/analytics/dashboard?months=`. Tests `tests/test_hr_analytics.py` (2).

### User-based access (entitlement + role)
- Gate is now three-layer: tenant entitlement (the two flags) **+ per-user HR role**. `require_hr_context`
  takes `roles=` — mutating endpoints require `HR_MANAGE_ROLES` ({hr_manager, super_admin}); read
  endpoints default to `HR_READ_ROLES` ({hr_manager, payroll_auditor, super_admin}). Plain
  `tenant_admin` is NOT granted HR by default (must be given an HR role).
- New **`GET /business/hr/access`** — a never-403 entitlement probe returning
  `{available, enabled, entitled, role, can_manage, can_view, is_self}` so the dashboard can decide
  whether to render the HR menu and which actions to expose. Frontend wiring (MitraBooks `app.js`
  sidebar + screens) and the `employee_self` self-scoped surface remain the next (frontend) phase.

**v1 COMPLETE.** HR surface = **27 routes** under `/api/v1/business/hr/*`. HR tests: **56 green**;
broad regression (business/accounting/COA/tenant/platform): **341 green**. Deferred for later phases:
self-service check-in / Attendance-mode LOP; GL posting of F&F; appointment-letter PDF; Aadhaar
vault; recruitment/performance/shift modules.
