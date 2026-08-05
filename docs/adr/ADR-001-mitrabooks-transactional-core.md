# ADR-001: MitraBooks ERP is the transactional core

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** SanMitra unified platform  

## Context

Early OfficeMitra drafts positioned OfficeMitra AI as the central “operating system,” with MitraBooks, LegalMitra, GruhaMitra, and MandirMitra plugging into it. That would create a third competing shell and reverse the platform direction already locked in `AGENTS.md`.

## Decision

- **MitraBooks ERP** remains the transactional / business core (accounting, vouchers, inventory, GST/TDS, ERP workflows).
- **LegalMitra** remains a separate product experience.
- **OfficeMitra AI** is a thin AI capability / orchestration layer — not the primary application shell and not the owner of domain or accounting data.
- **InvestMitra** stays out of unified SanMitra backend, frontend, registry, billing, and E2E scope.

## Consequences

- OfficeMitra must not redefine COA, journals, parties, inventory, or legal custody.
- MVP UI ships inside the MitraBooks ERP shell (permissions-driven). A future standalone OfficeMitra experience is allowed only if it still consumes ERP/legal data via connectors and does not become the platform OS.
- Product diagrams and marketing must not show OfficeMitra above MitraBooks as the system of record.
