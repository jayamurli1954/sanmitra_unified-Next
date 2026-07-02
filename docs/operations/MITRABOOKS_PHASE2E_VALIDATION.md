# MitraBooks Phase 2E Validation Gate

## Purpose

Phase 2E is the production-readiness gate for MitraBooks ERP core after the local implementation phases. It does not add new business functionality. It proves that the current ERP shell and accounting foundation can be trusted for staged rollout decisions.

## Current State

- Phase 2A through Phase 2D are implemented locally per the roadmap, with Phase 2D limited to review-first shells rather than live provider execution.
- Local browser smoke exists for global navigation, MitraBooks shell workflows, and CA invite acceptance.
- Backend tests exist for accounting invariants, posting rollback behavior, app-key isolation, tenant context, module access, and MitraBooks ERP core route behavior.
- Staging deployment automation exists in GitHub workflows, but staging execution may still be blocked by GitHub/Vercel permissions, Render access, DNS, or a missing safe demo tenant.

## Target State

Phase 2E is closed only when all of the following are true:

- Accounting guardrail tests pass for balanced postings, immutability, reversals, validation, and cross-store failure handling.
- Tenant/app isolation tests pass for accounting rows, protected routes, module access, and app-key context.
- Browser E2E smoke passes for the MitraBooks ERP shell, core navigation/workflow surfaces, and CA invite acceptance.
- Staging/deployment validation is recorded against a safe staging/demo URL without mutating real tenant data.
- Any blocked staging checks are explicitly documented as deployment/credential/tenant-policy gaps, not product-complete evidence.

## Repeatable Local Gate

Run:

```powershell
python scripts/mitrabooks_phase2e_gate.py
```

This executes:

- Focused accounting guardrail pytest files.
- Focused tenant/app isolation pytest files.
- Local Playwright smoke for global navigation, MitraBooks shell, and CA invite acceptance.

For a safe staging/demo frontend URL, run:

```powershell
python scripts/mitrabooks_phase2e_gate.py --staging-url https://example-staging-url
```

The staging mode is read-only browser smoke. Destructive staging checks are governed by the Phase 3 MitraBooks business demo policy: only `demo-mitrabooks-business`, only with staging-only demo credentials, only after reset/reseed, and only after the guarded policy check in `scripts/mitrabooks_phase3_business_gate.py` passes.

When the URL points directly to `/mitrabooks-erp/`, the gate runs the MitraBooks ERP shell smoke only for staging. The global launcher smoke is reserved for staging URLs that serve the SanMitra local/global frontend launcher at `/`.

## Validation Matrix

| Gate area | Local evidence | Required before Phase 2E closeout | Current status |
| --- | --- | --- | --- |
| Accounting guardrails | `scripts/mitrabooks_phase2e_gate.py` focused pytest group | Passing local gate and CI preflight | Passed locally on 2026-07-01: 40 focused tests |
| Tenant/app isolation | `scripts/mitrabooks_phase2e_gate.py` focused pytest group | Passing local gate and CI preflight | Passed locally on 2026-07-01: 67 focused tests |
| Browser E2E depth | Local Playwright smoke for global, MitraBooks shell, and CA acceptance | Passing local gate plus `python scripts/preflight.py --frontend` before push | Passed locally on 2026-07-01: 3 global, 3 MitraBooks shell, and 3 CA invite Playwright checks |
| Staging deployment | GitHub Render/Vercel workflows and optional `--staging-url` smoke | Successful deployment plus read-only staging smoke evidence | Passed read-only smoke on 2026-07-02 against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |
| Production readiness | Staged E2E evidence and deployment signoff | Phase 2E passed, no open critical tenant/accounting/security blockers | Phase 2E validation gate passed; broader production readiness still depends on later phase/deferred-scope signoffs |

## Latest Local Run

2026-07-01:

```powershell
python scripts/mitrabooks_phase2e_gate.py
```

Result:

- PASS: accounting guardrail pytest group, 40 tests.
- PASS: tenant/app isolation pytest group, 67 tests.
- PASS: local Playwright global smoke, 3 checks.
- PASS: local Playwright MitraBooks shell smoke, 3 checks.
- PASS: local Playwright CA invite acceptance smoke, 3 checks.
- SKIPPED: staging/deployment smoke because no safe staging/demo URL was provided.

2026-07-02:

```powershell
python scripts/mitrabooks_phase2e_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

Result:

- PASS: accounting guardrail pytest group, 40 tests.
- PASS: tenant/app isolation pytest group, 67 tests.
- PASS: local Playwright global smoke, 3 checks.
- PASS: local Playwright MitraBooks shell smoke, 3 checks.
- PASS: local Playwright CA invite acceptance smoke, 3 checks.
- PASS: read-only staging MitraBooks ERP shell smoke, 3 checks.
- Note: the approved staging URL points directly to `/mitrabooks-erp/`, so the local launcher/global staging smoke is intentionally skipped.

## Gaps

- Browser E2E is still smoke-depth, not full create-post-report-reverse coverage for every implemented business workflow.
- Staging validation cannot be considered complete from local tests alone.
- Live GST/e-way bill APIs, bank execution, OCR/AI auto-posting, AI MIS, advanced inventory depth, full export governance, and mobile apps remain deferred.

## Non-Goals

- Do not treat Phase 2E as live GST, bank payment, OCR, AI, or mobile enablement.
- Do not run destructive staging checks against real tenant data.
- Do not move to later GruhaMitra or combined ERP E2E gates until this stage has a recorded pass or an explicit documented exception.
