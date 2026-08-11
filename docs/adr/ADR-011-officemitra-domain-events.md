# ADR-011: OfficeMitra domain events (event bus)

**Status:** Proposed  
**Date:** 2026-08-07  
**Product scope:** OfficeMitra AI platform backbone (planned after ADR-009)  
**Depends on:** [ADR-008](ADR-008-officemitra-confirmed-writeback.md); beneficial after [ADR-009](ADR-009-officemitra-workflow-engine.md)  
**Does not supersede:** ADR-001–ADR-010  

## Context

ADR-008/009 execution is synchronous: confirm → executor → handler → (optional next step). As OfficeMitra grows, handlers that directly call notification, reminder, dashboard, and analytics services create tight coupling and duplicate side effects. An internal event bus lets “task created” fan out to listeners without changing the proposal/confirm path.

## Decision

1. **Introduce tenant-scoped domain events** emitted after successful Action Executor applications (and optionally after workflow step completion), for example `officemitra.task.created`, `officemitra.proposal.applied`, `officemitra.workflow.step.failed`.
2. **Events are additive:** they do not replace proposals, confirmations, or the Action Executor. Mutation still requires ADR-008/009/010 governance.
3. **Delivery model (first slice):** in-process pub/sub or Mongo outbox within the unified backend. External brokers (Kafka, etc.) are out of scope until a later revision.
4. **Listeners may:** create OfficeMitra notifications, enqueue reminders, update analytics counters — all tenant-scoped, fail-soft, and idempotent where practical.
5. **Listeners must not:** post journals, write companion DBs directly, or bypass Action Registry for mutations that require confirmation.
6. **Non-goals:** multi-region event mesh, customer-facing webhooks marketplace, InvestMitra.

## Consequences

- Workflow steps can stay thin; side effects move to event listeners.
- Tests must prove: events carry `tenant_id`; cross-tenant delivery impossible; listener failure does not roll back an already-applied action unless explicitly designed with outbox compensation.
- Acceptance authorizes design/spike; production event bus needs retention and PII policy review.
