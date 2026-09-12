# OfficeMitra Review Workspaces

**Document type:** Product requirements (current / target / gap)  
**Product:** OfficeMitra AI  
**Status:** Implemented behind flags (default off); demo-tenant smoke on `demo-mfg-mis`  
**Version:** 1.1  
**Date:** 2026-09-12  
**ADR:** [ADR-015](../adr/ADR-015-officemitra-review-workspaces.md)  
**Depends on:** [ADR-014](../adr/ADR-014-officemitra-ca-analysis-pack.md), SSDV as an internal engine (`D:\SSDV`)

This is the engineering contract for the next OfficeMitra slice. It is **not** a new product brand and it does **not** add Mitra names.

---

## Positioning

OfficeMitra remains one product: a thin AI / review layer on SanMitra. MitraBooks stays books of record. LegalMitra stays the separate professional product. SSDV stays internal (library/job — users never see the CLI).

**Build now (three workspaces, not three brands):**

| Workspace | Job |
| --- | --- |
| Review | Upload or connect period books, run a scan, show findings and a risk view |
| Working papers | Generate a small set of review-ready schedules and export Excel/PDF |
| Review notes | Assign findings, attach evidence, close the loop |

**Later (packages inside OfficeMitra, still not brands):** clients/documents, compliance calendar, knowledge, notices, advisory, team, analytics. Do not start those in this slice.

Do not introduce ClientMitra, ComplianceMitra, ReviewMitra, KnowledgeMitra, NoticeMitra, AdvisoryMitra, TeamMitra, AnalyticsMitra, or PracticeOS as product brands.

---

## Current state

What exists today and can be reused:

| Area | Current |
| --- | --- |
| Auth, RBAC, tenants, `X-App-Key`, audit | Built |
| OfficeMitra module `office_ai` | Built (tasks, brief, calendar, notes inbox, write-back, workflows, policy) |
| CA Analysis Pack (ADR-014) | Built behind `office_ai.mis*`: Excel import, MIS fact store, data quality score, attributed narrative, reconcile, Excel/PDF/PPT export. Remaining: live MitraBooks MIS reads and demo CA/MIS staging smoke |
| MitraBooks reports | Trial balance, ageing, P&L/BS, bank recon, GSTR-2B/ITC, TDS working paper, report export |
| MitraBooks CA practice | Client master, per-client books, staff-side document queue — **not** a client self-portal |
| Data Health | Rule findings on MitraBooks books |
| SSDV (`D:\SSDV`) | Library: journals, validate, trial balance, ageing, MIS snapshot, explain/red flags, CSV and Tally XML/HTTP connect. Local SQLite + Streamlit. No multi-tenant cloud API. No lead-schedule factory |
| These three workspaces | **Implemented behind flags (default off)** in OfficeMitra. Live MitraBooks ERP tenants are unchanged until `office_ai.review*` is explicitly enabled. |

---

## Target state (this slice)

An accountant in OfficeMitra (standalone or ERP panel) can:

1. Open an **engagement** (tenant-scoped; optional link to a CA `accounting_entity_id` / MIS `pack_id`).
2. Ingest India Excel/CSV (reuse ADR-014 template import). Optionally run SSDV in-process on a **review sandbox** — never into the live MitraBooks PostgreSQL ledger.
3. See **Review**: deterministic findings (`finding_code` + `rule_version`), a risk score that is **not** the MIS `data_quality_score`, and SSDV rule text (no LLM dashboard copy in this slice).
4. Generate **Working papers**: Cash, AR, AP lead schedules plus AR/AP ageing; Excel export; PDF if already cheap from MIS export. Hash + generator version on each artifact. Immutable after partner/manager close.
5. Raise **Review notes** from a finding, assign, attach evidence, move Open → Assigned → Resolved → Closed, using OfficeMitra tasks/policy rather than a third task system.

India only. Rule-based scan. Dashboard reads cached scan results (&lt;3s). Generation is async (working papers &lt;30s target, not a synchronous REST timeout).

---

## Gap (must be built)

- Module flags (default off): `office_ai.review`, `office_ai.review.working_papers`, `office_ai.review.notes`. Parent `office_ai` and `office_ai.mis` do not enable Review by themselves.
- Engagement + SourceFile + ReviewIssue + WorkingPaper records (Mongo, tenant-scoped). Link notes to `office_ai` tasks.
- SSDV in-process job wrapper (no CLI, no Streamlit). Review sandbox / MIS facts only.
- Review UI in the OfficeMitra shell (and ERP OfficeMitra panel): Review, Working papers, Review notes. **Done** behind flags.
- Tests: tenant isolation, module gates, no live-ledger writes from ingest, finding codes stable, WP immutability after close, notes cannot leak across tenants. **Done** in `tests/test_office_ai_review.py`.
- Remaining: operator signoff of [`docs/operations/OFFICEMITRA_REVIEW_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_REVIEW_SMOKE_CHECKLIST.md) on local/staging `demo-mfg-mis`.

---

## Deferred (explicit)

| Item | Why deferred |
| --- | --- |
| Client self-portal, AI document classify, missing-doc requests | CA staff queue already exists; portal is a later OfficeMitra package |
| Compliance calendar, knowledge/RAG, tax notices | LegalMitra CA persona / RAG; later OfficeMitra packages if composed, not rebuilt |
| Advisory opportunities, timesheets, capacity, firm analytics | After Review is used |
| Tally XML as a must-have, QuickBooks, Xero, Zoho OAuth | CSV/Excel first. SSDV Tally path optional follow-on |
| LLM explanations, agentic auto-requests, CaseWare/CCH | Phase 2+ of Review, with fact citations (ADR-014 / ADR-006) |
| Five-country packs (Canada, Singapore, UK, Australia) | Target for a later jurisdiction pack; SSDV/GST are India-native |
| New Mitra product names or a PracticeOS brand | Rejected for this slice ([ADR-015](../adr/ADR-015-officemitra-review-workspaces.md)) |

---

## Accounting boundary

- MitraBooks PostgreSQL remains books of record for ERP tenants ([ADR-001](../adr/ADR-001-mitrabooks-transactional-core.md)).
- Uploaded journals/TB must not `post()` into live tenant ledgers.
- Money: fixed-precision decimals or integer minor units — never float.
- No invoices, payroll, tax-return engine, or GST filing from Review flows.
- GST/bank rec screens that already exist in MitraBooks are reused, not rewritten.

---

## Roles (map to existing RBAC — do not invent a new role taxonomy)

| Practice label | Access in this slice |
| --- | --- |
| Partner | Full review workspace; close/lock working papers |
| Manager | Assign notes; review findings |
| Reviewer | Run scan; create notes |
| Accountant | Assigned notes and generated papers only |

Client portal login is out of scope.

---

## Implementation sequence

1. Registry flags + empty routes behind `office_ai.review*`.
2. Engagement + ingest reuse of MIS Excel import.
3. SSDV scan job → ReviewIssue list + risk score.
4. Cash / AR / AP schedules + ageing Excel.
5. Notes wired to tasks + in-app notification.
6. Demo-tenant smoke on `demo-mfg-mis` (MIS manufacturing demo) — not production enablement. Seed: `scripts/seed_review_demo.py`. Checklist: [`docs/operations/OFFICEMITRA_REVIEW_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_REVIEW_SMOKE_CHECKLIST.md).

Do not start deferred packages until this sequence has a passing smoke on that demo tenant. Do not enable `office_ai.review*` on `demo-mitrabooks-business` or live ERP tenants.

---

## Success (this slice only)

Measure on a small sample of demo or opted-in engagements after the smoke exists. Do not claim 30–50% effort reduction until a baseline is recorded.

Ship criteria: a reviewer can ingest a template workbook, see coded findings, export three lead schedules, and close a note — all tenant-scoped, with no live ledger mutation.
