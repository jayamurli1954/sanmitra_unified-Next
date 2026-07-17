---
name: sanmitra-release-review
description: SanMitra release-readiness workflow for commits, PRs, pushes, deploys, release tags, rollback notes, CI failures, preflight validation, versioning, documentation readiness, and AGENTS.md PR acceptance checklist compliance.
---

# SanMitra Release Review

## Authority

- Treat `AGENTS.md` as mandatory policy and source of truth.
- Do not push or mark release work ready without the required local preflight result or a clear reason it was not applicable.
- Load `migration-safety` for schema, index, seed, data migration, backfill, or rollback work.
- Load `accounting-doctrine` for any release that changes financial posting, receipts, ledgers, reports, tax, or payment behavior.

## Workflow

1. Identify changed files and whether the change is backend, frontend, docs-only, migration, dependency, release, or deployment scope.
2. Confirm changed files are within `D:\sanmitra_unified-Next` and do not include secrets or generated runtime artifacts.
3. Confirm the PR acceptance checklist is satisfied or explicitly not applicable for the change type.
4. Confirm validation commands match risk:
   - Always before commit/push: `python scripts/preflight.py`
   - Frontend change: `python scripts/preflight.py --frontend`
   - Dependency/lockfile change: `python scripts/preflight.py --security`
   - Release: `python scripts/preflight.py --all` and release preflight
5. Confirm rollback/reversal notes exist for schema, release, tenant, accounting, or provider-risk changes.

Also confirm no blocked destructive shell commands were used (see `AGENTS.md` §5 Agent
Shell Command Guardrails); production deploy, force-push, hard reset/clean, and unscoped
DB drops require explicit user approval.

## Checklist

- Current state, target state, gap, and deferred scope are clear in docs or PR notes when relevant.
- InvestMitra remains excluded from unified backend, frontend deployment, module registry, billing, E2E, and release scope.
- Version and release tag rules are respected when producing a production release.
- CI failures are fixed locally rather than deferred to GitHub Actions.
- Staged E2E order is preserved: LegalMitra baseline, MitraBooks ERP core, MandirMitra, GruhaMitra, combined ERP regression.

## Output

- State whether the change is ready, blocked, or ready with risk.
- List missing validation, missing rollback notes, or missing checklist evidence.
- Do not claim tests or preflight passed unless the command was actually run and succeeded.
