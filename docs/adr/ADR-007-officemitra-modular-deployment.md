# ADR-007: OfficeMitra supports modular deployment

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** OfficeMitra AI  
**Supersedes / clarifies:** Informal “independently deployable” drafts; does **not** replace ADR-001 (MitraBooks remains the transactional core when ERP is present) or ADR-006 (AI providers).

## Context

Clients may request OfficeMitra AI alone (tasks, email summary, daily brief) without MitraBooks ERP, LegalMitra, GruhaMitra, or MandirMitra. The unified SanMitra backend already hosts MitraBooks, GruhaMitra, MandirMitra, and OfficeMitra as modules in one process. Splitting OfficeMitra into a second codebase would duplicate auth, tenancy, and AI plumbing.

## Decision

OfficeMitra **supports modular deployment** in one codebase:

1. **Primary profile:** OfficeMitra enabled inside the MitraBooks Unified Backend alongside ERP / housing / temple modules as needed.
2. **Standalone profile:** Only `office_ai` (and core `auth` / `users` / `audit`) enabled — no ERP required.
3. **Companion profiles:** OfficeMitra + any subset of enabled product modules (Business/ERP, Housing, Temple, Legal via connector).

Rules:

- OfficeMitra has **no mandatory runtime dependency** on MitraBooks, LegalMitra, GruhaMitra, or MandirMitra.
- Cross-module facts are gathered only through a **Connector Manager** that discovers available connectors at request time from `enabled_modules` (and app context).
- Missing or disabled connectors must **never** prevent startup, task/email features, or Daily Brief generation.
- When companion modules are absent, Daily Brief summarizes OfficeMitra-native data only (tasks, emails, notes).
- **Internal modules** (business/accounting, housing, temple) are reached via in-process service interfaces (still no direct DB access — ADR-002/003).
- **Separate products** (LegalMitra) use the same connector contract; InvestMitra remains out of unified scope.
- Do **not** treat OfficeMitra as the platform OS (ADR-001).

## Consequences

- Same `app/modules/office_ai/` package serves unified and standalone tenants.
- Module registry allows app keys: `officemitra`, `mitrabooks`, `legalmitra`, `gruhamitra`, `mandirmitra` (explicit list — not `*`).
- Deployment profiles are configuration (`enabled_modules` + optional `officemitra` app key), not separate repositories.
- Standalone UI may later ship as its own shell; MVP UI may remain an ERP panel when `mitrabooks` is the host app key.
