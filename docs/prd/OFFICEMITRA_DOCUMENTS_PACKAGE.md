# OfficeMitra Documents Package

**Document type:** Product requirements (current / target / gap)  
**Product:** OfficeMitra AI  
**Status:** Implemented behind flags (default off); demo-tenant smoke on `demo-mfg-mis`  
**Version:** 1.0  
**Date:** 2026-09-12  
**ADR:** [ADR-016](../adr/ADR-016-officemitra-documents-package.md)  
**Depends on:** [ADR-015](../adr/ADR-015-officemitra-review-workspaces.md) Review notes, MitraBooks CA staff document queue

This is a **package inside OfficeMitra**, not a new Mitra brand.

---

## Positioning

Staff accountants need to see which CA documents already sit in MitraBooks and point a Review note at one of them. OfficeMitra does not become the document store. MitraBooks remains the queue of record. Clients do not log in here.

**Build now:**

| Surface | Job |
| --- | --- |
| Documents tab | List the existing CA staff queue for the engagement book |
| Link | Store `ca_document_id` on a Review note |
| Unlink | Clear that link; do not delete the CA document |

**Not this slice:** client self-portal, AI classify, missing-doc emails to clients, OfficeMitra uploads into MitraBooks, GST/journal writes.

Do not introduce ClientMitra, DocumentsMitra, or PracticeOS.

---

## Current state

| Area | Current |
| --- | --- |
| MitraBooks CA practice | Client master, per-client books, staff document queue, attachments |
| OfficeMitra Review notes | Open → assigned → resolved → closed, plus OfficeMitra tasks |
| Cross-product DB | Forbidden ([ADR-003](../adr/ADR-003-no-cross-product-db-access.md)) |
| Companion writes | [ADR-010](../adr/ADR-010-officemitra-companion-writeback.md) still Proposed |

---

## Target state (this slice)

An accountant in OfficeMitra can:

1. Open **Documents** when `office_ai.documents` is on.
2. See CA queue rows for the selected engagement’s `accounting_entity_id` (default `primary`) via the MitraBooks connector.
3. Link / unlink a Review note to a `document_id` without mutating MitraBooks.
4. Be told that uploads and status changes happen in MitraBooks CA Practice (`ca-access`).

If `business` is not enabled, the queue is empty and `enabled` is false (fail-soft).

---

## Gap (must be built)

- Registry flag `office_ai.documents` (default off).
- Connector read of `list_ca_document_metadata` / `get_ca_document_metadata`.
- Review note field `ca_document_id`.
- Routes under `/api/v1/officemitra/documents/*`.
- Documents tab in the OfficeMitra shell.
- Tests: flag gate, tenant isolation, no OfficeMitra query of `business_ca_document_metadata`, no ledger posts.
- Demo seed on `demo-mfg-mis` only.

---

## Deferred (explicit)

| Item | Why deferred |
| --- | --- |
| Client self-portal | Later package; CA invite viewer already exists in MitraBooks |
| Create / upload / status from OfficeMitra | Companion write; needs Accepted ADR-010 |
| AI classify / missing-doc requests | After staff linking is used |
| Knowledge, notices, advisory | LegalMitra or later OfficeMitra packages |

---

## Accounting boundary

- No PostgreSQL ledger writes.
- No invoices, GST filing, or payroll from Documents flows.
- Linking a note is OfficeMitra Mongo only.

---

## Enablement

Lock smoke to `demo-mfg-mis`. Refuse `demo-mitrabooks-business` and production ERP tenants. Seed: `scripts/seed_documents_demo.py`. Checklist: [`docs/operations/OFFICEMITRA_DOCUMENTS_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_DOCUMENTS_SMOKE_CHECKLIST.md).
