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

**Consequences**

- AI outputs are advisory; UI must not present them as final legal or financial advice.
- Provider failure must fall back safely (no crash, clear user message).
- Phase 4 confirmed writes to OfficeMitra-owned collections are governed by [ADR-008](ADR-008-officemitra-confirmed-writeback.md) (`office_ai.writeback`, human confirmation, audit).
- Companion-product write automation still requires a dedicated later ADR + human confirmation UX — see Proposed [ADR-010](ADR-010-officemitra-companion-writeback.md).
