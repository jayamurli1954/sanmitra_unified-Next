# ADR-016: OfficeMitra Documents package (staff-side CA queue)

**Status:** Accepted  
**Date:** 2026-09-12  
**Accepted:** 2026-09-12  
**Product scope:** OfficeMitra AI — staff Documents package  
**Depends on:** [ADR-002](ADR-002-officemitra-connectors-only.md), [ADR-003](ADR-003-no-cross-product-db-access.md), [ADR-015](ADR-015-officemitra-review-workspaces.md)  
**Does not supersede:** [ADR-001](ADR-001-mitrabooks-transactional-core.md), [ADR-010](ADR-010-officemitra-companion-writeback.md) (still Proposed), LegalMitra as a separate product, MitraBooks CA practice queue ownership

PRD: [docs/prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md](../prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md)

## Context

Review notes (ADR-015) need evidence from the existing MitraBooks CA staff document queue. Rebuilding a second inbox, adding a client self-portal, or inventing a DocumentsMitra brand would fork CA practice and contradict OfficeMitra as a thin layer.

Platform owner decision: staff-side Documents is the next OfficeMitra **package**, not a new brand. Reuse the MitraBooks CA queue. Do not start a client portal.

## Decision

1. **Brands stay.** No ClientMitra, DocumentsMitra, or PracticeOS.

2. **Flag (default off):** `office_ai.documents`. Parent `office_ai` / `office_ai.review` do not enable it.

3. **Source of truth:** MitraBooks CA document metadata (`business_ca_document_metadata`) remains owned by the business module. OfficeMitra reads it **only** through the MitraBooks connector calling `ca_clients` service functions. No OfficeMitra Mongo query of that collection.

4. **OfficeMitra-owned write:** linking a Review note to a `document_id` is stored on the Review note (OfficeMitra Mongo). That is not a MitraBooks journal or CA-queue mutation.

5. **No companion writes in this slice.** Creating, uploading, classifying, or changing CA document status from OfficeMitra stays deferred until [ADR-010](ADR-010-officemitra-companion-writeback.md) is Accepted. Staff upload/status work stays in MitraBooks CA Practice (`ca-access`).

6. **No client portal, no AI classify, no client missing-doc requests** in this slice.

7. **Enablement:** demo smoke on `demo-mfg-mis` only. Do not enable on `demo-mitrabooks-business` or production ERP tenants.

## Consequences

- Implementation follows [OFFICEMITRA_DOCUMENTS_PACKAGE.md](../prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md).
- Standalone OfficeMitra without the `business` module fail-softs (empty queue, `business_module_off`).
- CA queue rows are read with MitraBooks `app_key` because that is where the staff queue lives; `tenant_id` still comes from trusted context.
