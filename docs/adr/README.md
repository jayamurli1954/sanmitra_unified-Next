# Architecture Decision Records (ADR)

Short, durable records of *why* foundational platform choices were made.

## How to use

1. Propose a decision in a PR or review note.
2. Add `docs/adr/ADR-NNN-slug.md` with Context / Decision / Consequences.
3. Link the ADR from the relevant implementation plan or PRD.
4. Do not silently reverse an ADR — supersede it with a new ADR that references the old one.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-mitrabooks-transactional-core.md) | MitraBooks ERP is the transactional core | Accepted |
| [ADR-002](ADR-002-officemitra-connectors-only.md) | OfficeMitra AI communicates only through connectors | Accepted |
| [ADR-003](ADR-003-no-cross-product-db-access.md) | Cross-product database access is prohibited | Accepted |
| [ADR-004](ADR-004-tenant-id-canonical.md) | `tenant_id` is the canonical tenancy identifier | Accepted |
| [ADR-005](ADR-005-officemitra-mvp-read-only.md) | OfficeMitra MVP integrations are read-only | Accepted |
| [ADR-006](ADR-006-ai-providers-replaceable.md) | AI providers are replaceable | Accepted |
| [ADR-007](ADR-007-officemitra-modular-deployment.md) | OfficeMitra supports modular deployment | Accepted |

## Related

- Implementation plan: [`docs/architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md`](../architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md)
- Platform policy: [`AGENTS.md`](../../AGENTS.md)
