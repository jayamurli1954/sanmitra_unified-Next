# ADR-009: OfficeMitra workflow engine (owned actions only)

**Status:** Accepted  
**Date:** 2026-08-07  
**Accepted:** 2026-08-11  
**Product scope:** OfficeMitra AI Phase 6  
**Depends on:** [ADR-008](ADR-008-officemitra-confirmed-writeback.md) (proposals, Action Registry + Capability Descriptors, Action Executor)  
**Does not supersede:** ADR-001, ADR-002, ADR-003, ADR-005 (companion read-only), ADR-007, ADR-008  
**Related (future):** [ADR-011](ADR-011-officemitra-domain-events.md), [ADR-012](ADR-012-officemitra-policy-engine.md), [ADR-013](ADR-013-officemitra-workflow-template-library.md)

## Context

ADR-008 established human-confirmed, action-based writes to OfficeMitra-owned collections (`Proposal → Confirm → Executor → handler`). Real office work is often multi-step: create a task, notify the owner, schedule a follow-up, and remind tomorrow. Hardcoding those chains inside generate/confirm handlers would duplicate ADR-008’s registry and make audit trails incomplete.

This ADR does **not** invent a second execution engine. Workflows only orchestrate repeated calls through the existing Action Executor.

## Decision

1. **Workflow Engine role:** orchestrate sequences of registered actions after (or as part of) confirmed proposals. Every step uses:

```text
Workflow step → Action Executor → registered handler → OfficeMitra service
```

2. **Ownership boundary unchanged:** workflows may only invoke Action Registry handlers whose `target_module` is `office_ai`. Companion mutations remain forbidden until [ADR-010](ADR-010-officemitra-companion-writeback.md) is Accepted.

3. **Separate templates from runs:**
   - **Workflow Template** (reusable definition): `template_id`, `name`, `version`, `description`, ordered `steps[]` (`step_id`, `action_type`, `payload`), `continue_on_failure`, tenant scope, `created_by` / `updated_by` (user or `system`).
   - **Workflow Run** (instance): `run_id`, `template_id` + `template_version`, optional `proposal_id`, `trigger_source` (`proposal` | `manual` | `scheduled` | `api`), `idempotency_key`, actor, `step_results[]`, overall status, `started_at` / `finished_at`.
   - Do not embed full template definitions inside every proposal.

4. **Run / step lifecycle:** `pending`, `running`, `applied`, `failed`, `skipped`, `cancelled`.

5. **Diagnostics on each step (required):**
   - `started_at` / `finished_at` / `duration_ms`
   - `retry_count`
   - `executor_version`
   - `error_message` when failed

6. **Idempotency:** starting a run with the same tenant-scoped `idempotency_key` returns the existing run (does not start a duplicate).

7. **Human governance:**
   - Starting a workflow requires confirmation / authenticated start under feature flag.
   - Feature flag: `office_ai.workflows` (opt-in; parent `office_ai` alone does not enable it).
   - Per-step confirmation / maker-checker derived from each action’s **Capability Descriptor** (and later [ADR-012](ADR-012-officemitra-policy-engine.md)).

8. **Failure policy:** default stop-on-failure; template may set `continue_on_failure` explicitly. No silent partial success.

9. **Non-goals:** BPMN marketplace (see ADR-013), cross-tenant workflows, companion-product steps, OAuth mail/calendar send, async event fan-out (see ADR-011).

## Consequences

- Phase 6 implementation builds on ADR-008 without redesigning proposals or inventing a parallel executor.
- Tests must cover: template vs run separation; idempotency; flag off → deny; tenant isolation; step diagnostics; failure policy; no companion writes.
- Companion orchestration remains forbidden until ADR-010 is Accepted.

## Implementation sketch

```text
Workflow Template (reusable)
        ↓ start (confirm / API) + idempotency_key
Workflow Run #N (trigger_source)
        ↓
Action Executor (step 1..N, office_ai only)
        ↓
Audit + run history (duration, retries, executor_version)
```
