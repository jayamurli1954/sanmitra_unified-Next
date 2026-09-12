# Agent ideas from agency-agents (reference only)

**Source catalog:** [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) — MIT-licensed prompt packs for Cursor, Claude Code, Codex, and similar tools.

**Current state:** SanMitra policy and behavior are governed by [AGENTS.md](../../AGENTS.md) and repo-local skills under [`.codex/skills/`](../../.codex/skills/). This document is a **borrow list**, not an install guide.

**Target use:** Mine checklists, deliverable formats, and review gates from external agents; rewrite anything adopted so it respects tenant isolation, accounting doctrine, LegalMitra attribution, current-vs-target language, and local preflight.

**Non-goals:** Do not install the full agency roster, do not replace `AGENTS.md`, do not add third-party agent files to this repository without explicit review, and do not treat generic prompts as production-ready SanMitra policy.

---

## Global adaptation rule

Before applying any borrowed pattern, prepend SanMitra constraints:

1. **Tenancy and access** — `tenant_id`, `app_key`, `organization_type`, `enabled_modules`, RBAC ([`tenant-context-routing`](../../.codex/skills/tenant-context-routing/SKILL.md)).
2. **Accounting** — double-entry, append-only posted entries, no direct balance mutation ([`accounting-doctrine`](../../.codex/skills/accounting-doctrine/SKILL.md)).
3. **Legal** — source attribution, human review, no final legal advice ([`legalmitra-compliance`](../../.codex/skills/legalmitra-compliance/SKILL.md)).
4. **Scope discipline** — current vs target / gap / deferred; no implied shipped features.
5. **Validation** — `python scripts/preflight.py` (and `--frontend` / `--security` when relevant) before push ([LOCAL_CI_AND_SECURITY_SOP.md](./LOCAL_CI_AND_SECURITY_SOP.md)).

Strip from upstream agents: personality-heavy tone, “agency” voice, and claims that features exist when master planning docs mark them as planned or gap.

---

## Shortlist — eight agents to borrow from

### 1. Minimal Change Engineer

| | |
|---|---|
| **Upstream** | [engineering-minimal-change-engineer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-minimal-change-engineer.md) |
| **Complements** | [`sanmitra-code-review`](../../.codex/skills/sanmitra-code-review/SKILL.md) |

**Borrow**

- Explicit “minimum viable diff” checklist before editing.
- “Fix only what was asked” gate when a task is review-only or question-only.
- Call out scope creep (drive-by refactors, unrelated formatting, new abstractions for one call site).

**Ignore**

- Generic stack advice that conflicts with existing repo conventions.
- Suggestions to add broad error handling or helpers for unlikely edge cases.

**Adapt for SanMitra**

- Add a pre-edit check: read surrounding code; match naming and patterns already in the module.
- Block accounting shortcuts (direct balance updates, posted-entry edits) even when they would be a “minimal” fix.

---

### 2. Test Automation Engineer

| | |
|---|---|
| **Upstream** | [testing-test-automation-engineer.md](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-test-automation-engineer.md) |
| **Complements** | [`sanmitra-frontend-qa`](../../.codex/skills/sanmitra-frontend-qa/SKILL.md), [STAGED_E2E_PLAN.md](./STAGED_E2E_PLAN.md) |

**Borrow**

- Flake taxonomy: timing, locale/date, signed-out shell, missing API mocks, shared state.
- Trace-first debugging (Playwright trace, screenshot on failure).
- CI parallelization and deterministic wait patterns (prefer role/locator over arbitrary `sleep`).

**Ignore**

- Destructive E2E against non-demo tenants or production URLs.
- “Green at any cost” patterns that skip tenant or module gates.

**Adapt for SanMitra**

- Stage E2E in policy order: LegalMitra baseline → MitraBooks ERP → MandirMitra → GruhaMitra → combined regression.
- Mock `/access` and content endpoints when capturing manual or smoke screenshots (HR, MFG, OfficeMitra).
- Require demo tenant scope and documented confirm env vars for any destructive demo gate.

---

### 3. Technical Writer

| | |
|---|---|
| **Upstream** | [engineering-technical-writer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-technical-writer.md) |
| **Complements** | User manuals (`docs/MitraBooks_User_Manual.docx`), ops runbooks under `docs/operations/` |

**Borrow**

- Task-oriented structure: goal → prerequisites → numbered steps → expected outcome.
- Figure placement immediately after the heading they illustrate.
- Optional-feature labeling in TOC and body (e.g. “Optional add-on”, “Optional module”).
- Glossary and “common errors” sections tied to real UI labels.

**Ignore**

- Marketing tone and feature claims not backed by the product.
- Generic screenshots or placeholder flows.

**Adapt for SanMitra**

- Use exact product names: GruhaMitra, MandirMitra, MitraBooks, LegalMitra, OfficeMitra AI.
- Mark optional modules/add-ons consistently; distinguish current vs target in prose.
- Regenerate TOC programmatically or refresh Word fields after section renumbering (`scripts/rebuild_manual_toc.py`).

---

### 4. RAG Pipeline Engineer

| | |
|---|---|
| **Upstream** | [engineering-rag-pipeline-engineer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-rag-pipeline-engineer.md) |
| **Complements** | [`legalmitra-compliance`](../../.codex/skills/legalmitra-compliance/SKILL.md), OfficeMitra MIS (ADR-014) |

**Borrow**

- Chunking strategy notes (statute vs commentary vs user upload).
- Hybrid retrieval and re-ranking evaluation loops.
- “Citation required” output contract for every retrieved claim.
- Eval-driven iteration (golden questions, regression set for retrieval quality).

**Ignore**

- Vector DB or multi-model marketplace assumptions not in SanMitra scope.
- Writes from MIS/RAG flows into journals, invoices, or GST.

**Adapt for SanMitra**

- LegalMitra: never return research without source attribution and retrieval dates where law may change.
- OfficeMitra MIS: facts immutable after reconcile/export; narrative must cite facts; no GL writes from MIS flows.
- Tenant-scoped document indexes only; no cross-tenant retrieval.

---

### 5. AI-Generated Code Security Auditor

| | |
|---|---|
| **Upstream** | [security-ai-generated-code-auditor.md](https://github.com/msitarzewski/agency-agents/blob/main/security/security-ai-generated-code-auditor.md) |
| **Complements** | [`sanmitra-security-review`](../../.codex/skills/sanmitra-security-review/SKILL.md) |

**Borrow**

- Checklist for vibe-coded apps: hardcoded secrets, trust of client-supplied `tenant_id`, missing auth on new routes.
- Prompt-injection sinks in tools that accept user or email content.
- Over-broad logging of tokens, payment payloads, or legal documents.

**Ignore**

- Generic “use a WAF” advice without mapping to this codebase.
- Blockchain/Web3 patterns irrelevant to SanMitra.

**Adapt for SanMitra**

- Cross-check every new protected route against module registry and app-key validation.
- Flag any PostgreSQL money field using float/double.
- Require human review for LegalMitra drafting and external provider calls when tenant policy restricts them.

---

### 6. Database Optimizer

| | |
|---|---|
| **Upstream** | [engineering-database-optimizer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-database-optimizer.md) |
| **Complements** | [`accounting-doctrine`](../../.codex/skills/accounting-doctrine/SKILL.md), [`migration-safety`](../../.codex/skills/migration-safety/SKILL.md) |

**Borrow**

- Index design tied to query shapes (tenant-scoped ledger lists, date-range reports).
- Slow-query investigation workflow (EXPLAIN, missing tenant predicate).
- Migration-safe index creation patterns (concurrent where supported, rollback notes).

**Ignore**

- Denormalized balance columns updated outside the accounting service.
- Destructive schema changes without approval and rollback plan.

**Adapt for SanMitra**

- Every accounting query must remain tenant-scoped; index recommendations must include `tenant_id`.
- PostgreSQL owns financial truth; MongoDB index work stays separate and tenant-scoped.
- Follow [`migration-safety`](../../.codex/skills/migration-safety/SKILL.md) for any DDL.

---

### 7. Codebase Onboarding Engineer

| | |
|---|---|
| **Upstream** | [engineering-codebase-onboarding-engineer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-codebase-onboarding-engineer.md) |
| **Complements** | [CURRENT_VS_TARGET.md](../architecture/CURRENT_VS_TARGET.md), [MODULE_REGISTRY.md](../architecture/MODULE_REGISTRY.md) |

**Borrow**

- Read-only exploration method: trace one request from route → service → store.
- Factual summaries with file paths and “current vs planned” labels.
- “Where to change X” maps for common tasks (new module flag, new voucher type, new connector).

**Ignore**

- Assumptions that all products share one frontend or one database.
- InvestMitra as part of unified deployment (excluded unless separate workstream).

**Adapt for SanMitra**

- Start from `AGENTS.md` and master planning docs; cite gap explicitly when code is ahead or behind docs.
- Separate MitraBooks ERP shell vs LegalMitra product experience vs OfficeMitra module flags.

---

### 8. Reality Checker

| | |
|---|---|
| **Upstream** | [testing-reality-checker.md](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-reality-checker.md) |
| **Complements** | [FOSS_QUALITY_SECURITY_E2E_SEQUENCE.md](./FOSS_QUALITY_SECURITY_E2E_SEQUENCE.md), stage smoke checklists under `docs/operations/` |

**Borrow**

- Evidence-based sign-off: screenshot, command output, or test name — not “looks fine”.
- Release gate questions: what was tested, on which tenant, with which credentials.
- Explicit “not verified” list when scope was skipped.

**Ignore**

- Sign-off without staged E2E discipline.
- Production testing without runbook and rollback path.

**Adapt for SanMitra**

- Align with stage order in [STAGED_E2E_PLAN.md](./STAGED_E2E_PLAN.md); do not advance stage without passing smoke or documented exception.
- Accounting changes require pytest accounting gates and idempotency checks where applicable.
- Include AGENTS.md PR acceptance checklist items in the evidence bundle.

---

## Optional later borrows (not in the core eight)

| Agent | Borrow when |
|-------|-------------|
| [Identity & Access Engineer](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-identity-access-engineer.md) | OAuth/SSO, SAML, or fine-grained ABAC beyond current RBAC |
| [Multi-Agent Systems Architect](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-multi-agent-systems-architect.md) | OfficeMitra workflows (ADR-008/009) need topology and failure-recovery patterns |
| [Evidence Collector](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-evidence-collector.md) | Standardizing screenshot naming and visual QA for manuals and E2E |
| [Payments & Billing Engineer](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-payments-billing-engineer.md) | Deepening Razorpay/webhook/idempotency runbooks beyond current ops docs |

---

## Already covered — skim only

| agency-agents theme | SanMitra authority |
|---------------------|-------------------|
| Generic backend / API design | `app/` patterns + [`mitrabooks-erp`](../../.codex/skills/mitrabooks-erp/SKILL.md) |
| Generic security architecture | [`sanmitra-security-review`](../../.codex/skills/sanmitra-security-review/SKILL.md) |
| Generic code review | [`sanmitra-code-review`](../../.codex/skills/sanmitra-code-review/SKILL.md) |
| Release / deploy | [`sanmitra-release-review`](../../.codex/skills/sanmitra-release-review/SKILL.md) + [RELEASE_AND_ROLLBACK.md](./RELEASE_AND_ROLLBACK.md) |
| Housing / temple / legal domain | [`gruhamitra-housing`](../../.codex/skills/gruhamitra-housing/SKILL.md), [`mandirmitra-admin`](../../.codex/skills/mandirmitra-admin/SKILL.md), [`legalmitra-compliance`](../../.codex/skills/legalmitra-compliance/SKILL.md) |
| Marketing, social, paid media divisions | Out of scope for this repository |

---

## How to use this document

1. **Read upstream agent** — one file at a time from the links above.
2. **Extract** — checklists, output formats, failure modes only.
3. **Rewrite** — merge into an existing `.codex/skills/` skill, an ops checklist, or a PR template bullet; never paste upstream personality verbatim.
4. **Validate** — if the borrowed idea affects code or tests, run `python scripts/preflight.py` before commit.

**Do not** run `./scripts/install.sh` from agency-agents against this repo without an explicit decision to add specific, reviewed files.

---

## Version history

| Date | Change |
|------|--------|
| 2026-08-12 | Initial borrow list (eight core agents + four optional); reference-only, no installs |
