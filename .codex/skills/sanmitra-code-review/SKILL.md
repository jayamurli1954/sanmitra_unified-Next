---
name: sanmitra-code-review
description: SanMitra code-review workflow for changed backend, frontend, tests, docs, scripts, migrations, or configuration. Use when the user asks for a review, asks whether a change is safe, or needs PR-readiness feedback focused on bugs, regressions, tenant isolation, app-key/module access, tests, and AGENTS.md compliance.
---

# SanMitra Code Review

## Authority

- Treat `AGENTS.md` as mandatory policy and source of truth.
- Do not replace domain skills. Load `tenant-context-routing`, `accounting-doctrine`, `legalmitra-compliance`, `mitrabooks-erp`, `mandirmitra-admin`, `gruhamitra-housing`, or `migration-safety` when the reviewed change touches those areas.
- Keep InvestMitra out of unified backend, frontend, tenant/module registry, release, and E2E scope unless the user explicitly opens a separate personal-use workstream.

## Review Order

1. Identify changed files and affected product context.
2. Check behavioral correctness and likely regressions first.
3. Check tenant isolation, app-key isolation, module access, and RBAC on protected paths.
4. Check accounting invariants for money, posting, receipts, collections, reports, or financial exports.
5. Check LegalMitra confidentiality, source attribution, provider fallback, and human-review gates when legal workflows are touched.
6. Check tests match risk and that docs distinguish current state, target state, gaps, and deferred scope.

## Findings Format

- Lead with findings, ordered by severity.
- Include file and line references for each actionable issue.
- Prefer concrete failure modes over broad advice.
- If no issues are found, say so and state remaining test gaps or residual risk.

## Checklist

- Tenant-owned reads, writes, updates, deletes, reports, and background jobs are tenant-scoped.
- Protected module routes validate trusted `app_key`, enabled module, role, and permission.
- Financial changes preserve double-entry integrity, precision-safe money, idempotency, and append-only posted entries.
- Cross-database workflows do not leave domain transactions completed when accounting posting fails.
- Legal outputs keep source attribution, confidentiality, and human review.
- Frontend changes render from enabled modules and permissions, not hardcoded product assumptions.
- Tests or explicit test rationale cover the changed risk area.
