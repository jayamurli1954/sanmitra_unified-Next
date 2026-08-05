# ADR-005: OfficeMitra MVP integrations are read-only

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** OfficeMitra AI MVP  

## Context

AI write-backs into ERP/legal workflows (create invoice, post journal, file GST, send legal notice) create accounting, tenancy, and confidentiality risk before human-approval and audit patterns are proven.

## Decision

For MVP (Phases 0–1):

- Connectors to MitraBooks / LegalMitra / MandirMitra / GruhaMitra are **read-only**.
- OfficeMitra may produce **summaries, drafts, suggested tasks, and insights** only.
- OfficeMitra **must not** post journal entries, create invoices, file GST, send legal notices, or mutate other products’ records without an explicit later ADR + human confirmation UX.

OfficeMitra may write to its **own** Mongo collections (`officemitra_tasks`, `officemitra_emails`, `officemitra_briefs`).

## Consequences

- AI outputs are advisory; UI must not present them as final legal or financial advice.
- Provider failure must fall back safely (no crash, clear user message).
- Phase 4+ write automation requires user confirmation, audit events, and product-owner approval before implementation.
