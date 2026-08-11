# Architecture Decision Records (ADR)

Short, durable records of *why* foundational platform choices were made.

## How to use

1. Propose a decision in a PR or review note.
2. Add `docs/adr/ADR-NNN-slug.md` with Context / Decision / Consequences.
3. Link the ADR from the relevant implementation plan or PRD.
4. Do not silently reverse an ADR — supersede it with a new ADR that references the old one.
5. **Proposed** ADRs document intent only; they do not authorize implementation until Status is **Accepted**.
6. **Future** ADRs capture direction without near-term implementation commitment.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-mitrabooks-transactional-core.md) | MitraBooks ERP is the transactional core | Accepted |
| [ADR-002](ADR-002-officemitra-connectors-only.md) | OfficeMitra AI communicates only through connectors | Accepted |
| [ADR-003](ADR-003-no-cross-product-db-access.md) | Cross-product database access is prohibited | Accepted |
| [ADR-004](ADR-004-tenant-id-canonical.md) | `tenant_id` is the canonical tenancy identifier | Accepted |
| [ADR-005](ADR-005-officemitra-mvp-read-only.md) | OfficeMitra MVP integrations are read-only | Accepted (companion products; partially superseded by ADR-008 for OfficeMitra-owned confirmed writes) |
| [ADR-006](ADR-006-ai-providers-replaceable.md) | AI providers are replaceable | Accepted |
| [ADR-007](ADR-007-officemitra-modular-deployment.md) | OfficeMitra supports modular deployment | Accepted |
| [ADR-008](ADR-008-officemitra-confirmed-writeback.md) | OfficeMitra confirmed write-back (owned collections only) | Accepted |
| [ADR-009](ADR-009-officemitra-workflow-engine.md) | OfficeMitra workflow engine (owned actions only) | Accepted |
| [ADR-010](ADR-010-officemitra-companion-writeback.md) | OfficeMitra companion write-back via connectors | Proposed |
| [ADR-011](ADR-011-officemitra-domain-events.md) | OfficeMitra domain events (event bus) | Proposed |
| [ADR-012](ADR-012-officemitra-policy-engine.md) | OfficeMitra policy and authorization engine | Accepted |
| [ADR-013](ADR-013-officemitra-workflow-template-library.md) | OfficeMitra workflow template library | Future |
| [ADR-014](ADR-014-officemitra-ca-analysis-pack.md) | OfficeMitra CA Analysis Pack (MIS, narrative, export) | Accepted |

## Layered execution model (OfficeMitra)

```text
AI → Proposal Engine → Confirmation / Policy (ADR-012)
        → Action Registry + Capability Descriptors (ADR-008)
        → Action Executor
        → Workflow Engine (ADR-009, optional multi-step)
        → Connectors (ADR-002 / ADR-010 writes)
        → Product services → Databases
```

Domain events (ADR-011) fan out side effects after successful applies without replacing this path.

MIS assembly (ADR-014) sits **above** read connectors: ingest/normalize facts → metric pack → narrative → policy-gated export. It does not replace the execution path for writes.

## Related

- Implementation plan: [`docs/architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md`](../architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md)
- Platform policy: [`AGENTS.md`](../../AGENTS.md)
