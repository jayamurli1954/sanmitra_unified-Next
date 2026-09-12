# ADR-017: OfficeMitra staff missing-document requests

**Status:** Accepted  
**Date:** 2026-09-12  
**Accepted:** 2026-09-12  
**Product scope:** OfficeMitra AI — Documents package follow-on  
**Depends on:** [ADR-016](ADR-016-officemitra-documents-package.md), [ADR-008](ADR-008-officemitra-confirmed-writeback.md) (OfficeMitra-owned tasks)  
**Does not supersede:** ADR-016, [ADR-010](ADR-010-officemitra-companion-writeback.md) (still Proposed), LegalMitra notices

PRD: [docs/prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md](../prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md) (v1.1)  
Implementation plan (for review): [OFFICEMITRA_DOCUMENTS_REQUESTS_IMPLEMENTATION_PLAN.md](../architecture/OFFICEMITRA_DOCUMENTS_REQUESTS_IMPLEMENTATION_PLAN.md)

## Context

Staff can list the MitraBooks CA queue and link Review notes (ADR-016). They still cannot see which expected India review papers are absent, except by eyeballing the queue. Client email / portal requests would be a different product (and a companion write).

## Decision

1. **Flag (default off):** `office_ai.documents.requests`. Requires parent `office_ai.documents`.

2. **Gap report:** compare a fixed India staff checklist (bank statement, GST working, TDS challans, trial balance, AR ageing) to CA queue `document_type` values for the engagement book. Deterministic. No LLM.

3. **Request:** create an OfficeMitra **task** (and optional Review note) for a missing type. Idempotent per tenant + engagement + document type while the task is open.

4. **Forbidden in this slice:** client portal, client email, WhatsApp, CA queue inserts, ledger writes, AI classify.

5. **Enablement:** `demo-mfg-mis` only, same as ADR-016.

## Consequences

- Missing-doc work stays inside OfficeMitra tasks/notes. Staff still upload in MitraBooks CA Practice.
- Adding new expected types is a checklist change, not a new brand.
