# ADR-008: OfficeMitra confirmed write-back (OfficeMitra-owned only)

**Status:** Accepted  
**Date:** 2026-08-06  
**Product scope:** OfficeMitra AI Phase 4  
**Supersedes (partially):** [ADR-005](ADR-005-officemitra-mvp-read-only.md) — MVP companion integrations remain read-only; this ADR authorizes **confirmed** writes to OfficeMitra-owned collections only.  
**Does not supersede:** ADR-001 (MitraBooks transactional core), ADR-002 (connectors only), ADR-003 (no cross-product DB), ADR-007 (modular deployment).

## Context

Phases 0–3 keep OfficeMitra advisory: summaries, drafts, suggested tasks, and read-only connector facts. Auto-writing into ERP/legal/housing/temple records remains high risk. Operators still need a human-in-the-loop path so AI suggestions can become real OfficeMitra records without silent mutation.

## Decision

1. **Action-based proposals (not task-hardcoded):** every proposal carries:
   - `action_type` (registered action key)
   - `target_module` (`office_ai` only in this ADR)
   - `payload`
   - optional `confidence` / `reasoning`
   - `requires_confirmation` (always true for Phase 4)
   - audit metadata (actor, timestamps, prompt/telemetry refs)
2. **Action Registry + Action Executor + Capability Descriptors:** confirm does not call product services directly. Flow is:
   `Proposal → Confirm → Action Executor → registered handler → OfficeMitra service`.
   First registered action: `create_task`. Every action carries an **Action Capability Descriptor** (`requires_confirmation`, `requires_maker_checker`, `risk_level`, `idempotent`, `rollback_supported`, `audit_level`) so UI/executor/audit derive behavior declaratively.
   Future OfficeMitra-owned actions register without redesigning confirm/dismiss.
3. **Lifecycle:** `draft → pending → confirmed → applied | failed`, plus `dismissed` from `pending`. Phase 4 create path starts at `pending`.
4. **Allowed writes:** OfficeMitra Mongo collections only via registered handlers. Still **forbidden** without a later ADR: journals, invoices, GST, legal notices, housing/temple mutations, companion DB writes.
5. **Feature flag (default off):** `office_ai.writeback` must be explicit in `enabled_modules` or `office_ai_features`. Parent `office_ai` alone does **not** enable write-back.
6. **Audit:** confirm/dismiss/fail/apply emit audit events with tenant, actor, proposal id, action type, and outcome. Applied tasks keep `source=ai`.
7. **Connectors remain read-only** for companion products.

## Consequences

- UI shows Confirm / Dismiss for pending proposals; advisory disclaimers remain.
- Tests prove: flag off → 403; dismiss → no mutation; confirm → tenant-scoped applied result; unknown action → failed; no accounting/legal side effects.
- ADR-005 continues to govern companion integrations as read-only until a dedicated companion write-back ADR.
- Workflow engines / cross-product orchestration / domain events / policy engine are deferred to [ADR-009](ADR-009-officemitra-workflow-engine.md) (Accepted; Phase 6), [ADR-010](ADR-010-officemitra-companion-writeback.md)–[ADR-012](ADR-012-officemitra-policy-engine.md) (Proposed), and [ADR-013](ADR-013-officemitra-workflow-template-library.md) (Future); this ADR only establishes the proposal + registry foundation.
