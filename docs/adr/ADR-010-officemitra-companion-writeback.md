# ADR-010: OfficeMitra companion write-back via connectors

**Status:** Proposed  
**Date:** 2026-08-07  
**Product scope:** OfficeMitra AI (post Phase 6; gated)  
**Depends on:** [ADR-002](ADR-002-officemitra-connectors-only.md), [ADR-008](ADR-008-officemitra-confirmed-writeback.md); optionally [ADR-009](ADR-009-officemitra-workflow-engine.md) for multi-step runs  
**Supersedes (partially, when Accepted):** [ADR-005](ADR-005-officemitra-mvp-read-only.md) companion read-only rule — only for explicitly allowlisted connector write operations  
**Does not supersede:** ADR-001 (MitraBooks remains transactional core), ADR-003 (no direct cross-product DB access)  
**Related:** [ADR-012](ADR-012-officemitra-policy-engine.md) for centralized maker-checker / RBAC policy evaluation  

## Context

ADR-005 / ADR-008 keep companion products read-only: OfficeMitra must not post journals, create invoices, file GST, send legal notices, or mutate housing/temple records. Operators will eventually want AI-assisted actions such as “draft maintenance follow-up” or “create ERP task note,” but silent or direct DB writes would break accounting doctrine, tenancy, and legal confidentiality.

## Decision

1. **Companion mutations only through write-capable connectors** that call each product’s **existing service layer** (never Mongo/SQL from `office_ai`):

```text
Proposal / Workflow step
        ↓ confirm (+ maker-checker when required)
Action Executor
        ↓
Write connector → product service → domain result
        ↓
Audit
```

2. **Allowlist, not blanket module write access.** Register specific actions only, for example:
   - Allowed: `housing.add_comment`, `legal.create_draft`, `business.attach_note`
   - Not allowed by default: `accounting.insert_journal`, `legal.send_notice`, GST portal filing

3. **Action Capability Descriptor (required on every companion action):**

| Field | Purpose |
| --- | --- |
| `requires_confirmation` | Always true for companion writes in Phase 1 of this ADR |
| `requires_maker_checker` | Dual approval for HIGH/CRITICAL risk |
| `risk_level` | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `idempotent` | Safe to retry with same idempotency key |
| `rollback_supported` | Whether a compensating action exists |
| `audit_level` | `BASIC` / `STANDARD` / `FULL` |

UI, executor, and audit derive behavior from this metadata instead of scattered conditionals.

4. **Feature flags (default off):** `office_ai.companion_writeback` plus optional per-target flags. Parent `office_ai` alone does not enable companion writes.

5. **Hard exclusions (remain forbidden unless a later ADR says otherwise):**
   - direct journal / ledger mutation outside the accounting service,
   - GST return filing / government e-invoice submission,
   - sending external legal notices or mail without human review,
   - InvestMitra (out of unified scope).

6. **Accounting doctrine (permanent):** any financial effect must go through MitraBooks accounting services (double-entry, fixed-precision money, idempotency, append-only posted entries). **OfficeMitra never inserts journal rows itself.**

7. **Failure modes:** connector/service failure → proposal/workflow step `failed`; no fake success in OfficeMitra UI; domain compensation follows the product service.

## Consequences

- ADR-005 companion read-only remains in force until this ADR is **Accepted** and tenant flags are enabled.
- Implementation adds connector write methods, registry entries with capability descriptors, audit fields, and isolation tests.
- Ship one allowlisted companion action at a time (prefer non-financial comment/draft actions before any financial posting).
- Proposed status is **not** authorization to ship companion writes.

## Sequencing

1. Accept/implement [ADR-009](ADR-009-officemitra-workflow-engine.md) first (owned multi-step, lower risk). — **Done**
2. Prefer [ADR-012](ADR-012-officemitra-policy-engine.md) Accepted before HIGH/CRITICAL companion actions. — **Done (Accepted 2026-08-11)**
3. Accept ADR-010 when the first allowlist and capability descriptors are specified by product owner.
