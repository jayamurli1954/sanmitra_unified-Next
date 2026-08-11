# ADR-012: OfficeMitra policy and authorization engine

**Status:** Accepted  
**Date:** 2026-08-07  
**Accepted:** 2026-08-11  
**Product scope:** OfficeMitra AI governance layer  
**Depends on:** [ADR-008](ADR-008-officemitra-confirmed-writeback.md) Action Capability Descriptors; enables [ADR-010](ADR-010-officemitra-companion-writeback.md) maker-checker at scale  
**Related:** [ADR-009](ADR-009-officemitra-workflow-engine.md) (workflows call the same policy API before steps/runs)  
**Does not supersede:** platform RBAC in `app.core` — this ADR specializes OfficeMitra action policy evaluation  

## Context

Capability Descriptors on each action declare `requires_confirmation`, `requires_maker_checker`, `risk_level`, etc. Without a central policy engine, confirm/executor/workflow/connector code accumulates ad-hoc role checks that drift. Companion writes (ADR-010) must not ship broadly without shared enforcement.

## Decision

1. **Introduce an OfficeMitra Policy Engine** that evaluates **before** Action Executor runs (never after). UI, proposal confirm, workflow start, and future connectors share one API.

2. **First-class `PolicyContext` input** (same shape everywhere):
   - `tenant_id`, `actor_id`, `actor_roles`
   - `action_type`, `target_module`
   - `feature_flags` / enabled modules
   - `intent` (`propose` | `confirm` | `approve` | `execute` | `start_workflow`)
   - `approval_state` (maker_id, checker_id, confirmed_at, expires_at, …)
   - optional `proposal_id` / `workflow_run_id`

3. **Structured decision payload** (not enum-only):

```yaml
allowed: true|false
execution_mode: deny | immediate | confirmation | maker_checker
decision: ALLOW | DENY | REQUIRE_CONFIRMATION | REQUIRE_MAKER_CHECKER  # compat label
rule_id: POL-021
reason: "office_ai.writeback disabled"
approval_expiry_hours: 72   # when maker_checker / confirmation holds apply
```

4. **Formal evaluation order:**
   1. Module `office_ai` enabled?
   2. Required feature flag enabled? (`writeback` / `workflows` / future `companion_writeback`)
   3. Action registered?
   4. Actor authorized (authenticated + role/permission gates when present)?
   5. Capability Descriptor rules (`requires_confirmation`, `requires_maker_checker`, `risk_level`)?
   6. Maker–checker / approval expiry state?
   7. Final decision

5. **Maker–checker:** maker ≠ checker by default. Same user cannot approve their own confirmation unless tenant explicitly enables self-approval. Pending approvals expire after `approval_expiry_hours` (default **72**); expired proposals must restart.

6. **Audit:** every policy decision is logged with tenant, actor, action_type, structured outcome, and `rule_id`.

7. **Non-goals:** replacing platform-wide authN; general OPA product UI; companion allowlists (that is ADR-010).

## Consequences

- UI and executor share one policy API instead of duplicated conditionals.
- ADR-012 sits between ADR-009 and ADR-010: governance before broad companion writes.
- Domain-event consumers (ADR-011) must not bypass policy; evaluate before execution only.
- Tests: deny when flag off; maker≠checker; approval expiry; rule_id present; tenant isolation of approval records.
