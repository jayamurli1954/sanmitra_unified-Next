# LegalMitra Stage 6 — Platform Ecosystem

**Document type:** Implementation specification  
**Product:** LegalMitra (with selective SanMitra shared services)  
**Status:** Implemented (MVP — feature-flagged)  
**Version:** 1.1  
**Date:** 2026-08-02  
**Companion PRD:** [`docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md`](../prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md)  
**Depends on:**  
- Stage 3 practice context ([`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md))  
- Stage 4 proactive surfaces ([`LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md`](LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md))  
- Stage 5 guided workflows ([`LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md`](LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md))  
- Accounting doctrine ([`ACCOUNTING_DOCTRINE.md`](ACCOUNTING_DOCTRINE.md))

This document is the engineering contract for **Stage 6 (Platform Ecosystem)**.  
It connects LegalMitra practice value to shared SanMitra capabilities — especially **optional fee posting into MitraBooks accounting** — without merging LegalMitra into the MitraBooks ERP frontend or duplicating unsafe AI paths.

---

## 1. Why Stage 6 exists

| Stage | What it established |
| --- | --- |
| 2 | Trust — grounded research |
| 3 | Context — clients, matters, documents |
| 4 | Proactivity — Morning Brief, alerts |
| 5 | Guided execution — human-gated workflows |
| **6** | **Platform leverage** — shared services + optional accounting for practice fees |

Stage 6 answers: *“Record and collect practice fees safely, reuse platform primitives where justified, and keep LegalMitra a distinct professional product.”*

Product posture remains **AI Professional Assistant**, not “AI Lawyer,” and **not** “LegalMitra inside MitraBooks ERP.”

---

## 2. Current vs target vs gap

| Layer | Current state | Target (Stage 6) | Gap |
| --- | --- | --- | --- |
| Practice fees | Live fee summary + invoice list on tracker (when billing enabled) | LegalMitra-native fee ledger + GST-capable client invoices | Broader invoice UX; optional MitraBooks posting still flagged off by default |
| Accounting | MitraBooks posting unused by LegalMitra | Optional post of **collected** fees via shared accounting service | Cross-db boundary + idempotency + reversals |
| Time | Not tracked | Optional time entries linked to matters | `legal_time_entries` + report rollups |
| Notifications | LegalMitra in-app only | Optional reuse of shared notification patterns | Thin adapter; no product merge |
| Documents | Matter docs in LegalMitra | Shared document retention/audit patterns where justified | Policy alignment, not one UI |
| Shared AI | LegalMitra-only research/workflows | Reuse safe patterns (refusal, attribution, review gates) — **not** a multi-product AI brain dump | Documented shared helpers only |
| Product UX | Separate LegalMitra frontend | Remains separate (`LM-SCOPE-2`) | No ERP shell merge |

**Non-goals (Stage 6) — do not build:**

- Merging LegalMitra into MitraBooks Unified ERP frontend  
- Direct PostgreSQL ledger inserts/updates from LegalMitra  
- Auto-posting fees without human confirm  
- Spreading Stage 2/5 AI surfaces to MandirMitra / GruhaMitra by default  
- Full Legalit practice OS parity  
- InvestMitra (out of unified scope)  
- Court cause-list sync as a dependency for fee posting  
- Autonomous billing agents  

---

## 3. Prerequisites

1. Stages 3–5 stable on the working branch (practice data, Morning Brief, at least one guided workflow).  
2. Accounting service posting path green for MitraBooks business demo (double-entry, idempotency, reversals).  
3. Explicit platform-owner decision before enabling fee→GL posting for any paying LegalMitra tenant.  
4. Feature flags: `LEGALMITRA_BILLING_ENABLED`, `LEGALMITRA_MITRABOOKS_POSTING_ENABLED` (default **false** in production).  
5. Adoption gate: prefer waiting until LegalMitra has meaningful paid usage before broad shared-AI expansion.

---

## 4. MVP scope (narrow)

### 4.1 LegalMitra-native practice billing (required MVP)

```text
Matter / Client
  → Fee note / invoice draft (LegalMitra Mongo)
  → Human review + mark issued
  → Record collection (partial / full)
  → Optional: Post collection to MitraBooks GL (flagged)
```

MVP entities:

| Entity | Purpose |
| --- | --- |
| Fee note / invoice | Client-facing amount, GST fields, matter link, status |
| Fee line | Description, qty/hours, rate, tax |
| Collection | Amount received, mode, date, idempotency key |
| Time entry (optional) | Hours × rate → may seed fee lines |

Statuses (illustrative): `draft` → `issued` → `partially_paid` / `paid` → `void` (soft).  
Never delete issued invoices; void with audit.

### 4.2 Optional MitraBooks posting (flagged)

When `LEGALMITRA_MITRABOOKS_POSTING_ENABLED` and tenant has accounting module + linked business books context:

- Post **collections only** (cash/bank vs fee income / receivables per chart mapping).  
- Use shared accounting service only (`post_transaction` / journal API).  
- Store `journal_id` / posting reference on the collection.  
- Fail closed: if posting fails, collection must not look “posted to books.”  
- Corrections via accounting **reversal**, never ledger row edit.

### 4.3 Shared platform patterns (selective)

Reuse, do not fork dangerously:

| Pattern | Reuse approach |
| --- | --- |
| Audit | Existing `log_audit_event` |
| Tenant / app context | Existing trusted context helpers |
| Notifications | Optional shared envelope shape; LegalMitra remains delivery owner for practice alerts |
| Document retention metadata | Align field names / soft-archive rules |
| AI safety helpers | Citation/refusal/review flags as shared utilities **only if** extracted without product coupling |

---

## 5. Accounting integration contract

### 5.1 Hard rules ([`ACCOUNTING_DOCTRINE.md`](ACCOUNTING_DOCTRINE.md))

1. Debits = credits; fixed-precision money; no `float`.  
2. Posted journals immutable; reverse to correct.  
3. Every posting tenant-scoped; idempotency key required.  
4. No raw SQL/ORM balance mutation from LegalMitra.  
5. Cross-db: Mongo fee collection + Postgres posting must document completion boundary (prefer outbox or compensating rollback notes).

### 5.2 Suggested posting sketch (collections)

```text
Dr Bank / Cash          (asset increase)
Cr Fee income / AR      (per tenant chart mapping)
```

Mapping is tenant-configured (`legal_fee_gl_map`), not hard-coded account IDs in LegalMitra routes.

### 5.3 What never posts automatically

- Draft invoices  
- Unconfirmed collections  
- Workflow “ready_to_file” markers  
- Research or draft artifacts  

---

## 6. Data model (MongoDB + PostgreSQL)

Scoped by `tenant_id` + `app_key`. Never trust `tenant_id` from body.

### 6.1 Mongo (LegalMitra-owned)

| Collection | Notes |
| --- | --- |
| `legal_fee_invoices` | Invoice header, matter_id, client_id, status, GST fields, totals |
| `legal_fee_lines` | Or embedded lines on invoice |
| `legal_fee_collections` | Amount, mode, collected_at, `idempotency_key`, `accounting_posting_ref` |
| `legal_time_entries` | Optional; matter_id, minutes, rate, billable |
| `legal_fee_gl_map` | Tenant chart mapping for optional posting |

### 6.2 PostgreSQL (MitraBooks-owned)

| Store | Notes |
| --- | --- |
| Journals / lines | Only via accounting service when posting enabled |
| Chart of accounts | Tenant books; LegalMitra maps to account codes |

---

## 7. API surface (`/api/v1/legal`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/practice/fees/invoices` | List / create draft invoice |
| GET/PATCH | `/practice/fees/invoices/{id}` | Detail / update draft / void |
| POST | `/practice/fees/invoices/{id}/issue` | Human issue gate |
| POST | `/practice/fees/invoices/{id}/collections` | Record collection (+ optional post) |
| GET | `/practice/fees/summary` | Tracker fee widget (replace `—`) |
| GET/POST | `/practice/time-entries` | Optional time tracking |
| GET | `/practice/fees/gl-map` | Mapping read (admin) |

Module gate: `legal` (+ accounting module check only when posting).  
Audit issue / collect / void / post / reverse.

---

## 8. Frontend surfaces

- Tracker **Fees outstanding** metric from live summary (not `—`)  
- Fee ledger register (issue, record payment)  
- Matter detail: fees / time strip  
- Explicit “Post to MitraBooks” confirm when flag on — never silent  
- Preserve LegalMitra shell; deep-link to MitraBooks reports only if tenant has ERP access  

---

## 9. Safety rules (non-negotiable)

1. LegalMitra stays a **separate product experience**.  
2. No direct ledger mutation.  
3. No auto-post; human confirm for books posting.  
4. Tenant + app isolation on all fee/time records.  
5. Soft-void; keep audit.  
6. Do not invent fee balances or GST figures.  
7. Provider AI must not invent invoices or statutory fee schedules.  
8. Production posting disabled until owner enablement + accounting smoke pass.

---

## 10. Acceptance criteria

### Billing MVP exit

- [x] Create → issue → collect fee note for a matter with audit trail  
- [x] Tracker fee metric shows live summary for signed-in tenants  
- [x] Partial payment and void behave correctly  
- [x] Feature flag disables billing routes in production when off  
- [x] Tenant isolation verified  
- [x] Stages 2–5 tests still pass  

**Frontend / contract hardening (2026-08-16):** prod billing default off; tracker Issue/Collect/Void; HTTP isolation suite. Sign-off: [`docs/operations/LEGALMITRA_STAGE6_HARDENING_SIGNOFF.md`](../operations/LEGALMITRA_STAGE6_HARDENING_SIGNOFF.md). MitraBooks posting remains flagged off by default.

### MitraBooks posting exit (optional slice)

- [ ] Collection posts only through accounting service with idempotency  
- [ ] Failed posting does not leave “posted” domain state  
- [ ] Reversal path documented and tested  
- [ ] Debits equal credits on posted journals  
- [ ] No LegalMitra path writes journal lines directly  

### Shared-pattern exit

- [ ] At least one shared helper/pattern reused without duplicating unsafe AI  
- [ ] Docs distinguish current vs target vs gap; LegalMitra remains separate  

---

## 11. Implementation sequence

| Step | Work | Outcome |
| --- | --- | --- |
| 0 | Stage 3–5 green + flags | Safe base |
| 1 | Fee invoice/collection schemas + indexes | Data layer |
| 2 | Issue / collect APIs + audit + tracker summary | Billing MVP |
| 3 | Optional time entries | Billable hours |
| 4 | GL map + accounting adapter + idempotency | Posting slice |
| 5 | Cross-db failure tests + reversal notes | Accounting safety |
| 6 | Frontend fee ledger + confirm UX | Operator usable |
| 7 | Shared notification/doc metadata alignment (thin) | Ecosystem without merge |
| 8 | Preflight / regression | Exit |

---

## 12. Explicitly deferred

| Topic | When |
| --- | --- |
| Full practice OS (Legalit parity) | Only if north star requires a named slice |
| Multi-product AI Brain rollout | After LegalMitra trust + adoption; separate owner decision |
| Payroll / trust / temple fee patterns | Other products’ modules — not LegalMitra Stage 6 |
| Auto e-invoice IRN / GST portal push | Separate compliance project |
| Court fee calculators as SoT | Tools remain advisory |

---

## 13. Document control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-08-02 | Initial Stage 6 plan: native fee ledger, optional MitraBooks posting, selective shared patterns, LegalMitra remains separate |
| 1.1 | 2026-08-02 | MVP implemented: fee invoices/collections/time entries/summary, GL map + optional posting adapter, tracker fee panel |
| 1.2 | 2026-08-16 | Hardening: prod billing default off, tracker Issue/Collect/Void, HTTP tests, ops sign-off |
