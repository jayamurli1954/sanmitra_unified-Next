# ADR-003: Cross-product database access is prohibited

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** SanMitra modular monolith  

## Context

All products share one FastAPI process, one Mongo cluster, and one Postgres accounting database. Shared process ≠ shared ownership. Cross-product queries look convenient in a monolith and become unmaintainable quickly.

## Decision

- OfficeMitra (and any future cross-product feature) **must not** read or write another product’s Mongo collections or Postgres tables directly.
- Accounting data remains owned by the accounting / MitraBooks services; OfficeMitra never posts journals or mutates ledger rows.
- OfficeMitra’s own data lives in OfficeMitra Mongo collections only (`officemitra_*`), always scoped by `tenant_id`.
- **No new Postgres tables** for OfficeMitra MVP.

## Consequences

- Even “simple” SQL against accounting tables from OfficeMitra code is a policy violation.
- Cross-database consistency rules still apply if a future write path is approved (compensating actions, no completed-looking domain state when posting fails).
- Code review and AGENTS.md OfficeMitra section must call out this rule explicitly.
