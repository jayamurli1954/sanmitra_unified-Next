# MitraBooks Document Upload, Storage, and OCR Policy

## Current State

MitraBooks has a tenant-scoped document upload inbox for CA practice and bookkeeping workflows. The implemented local path supports:

- CA document metadata linked to tenant, app, accounting entity, and client book context.
- Attachment upload, listing, download, and attachment-count evidence for supported business document owners.
- Manual review status and timestamps.
- Audit events for upload, download, and review actions.
- Local backend and mocked-shell coverage for client/book selection, attachment evidence, and review advancement.

Uploaded documents are tenant-owned records. Protected routes must continue to resolve trusted tenant and app context from authentication/session middleware and request headers, not request-body tenant values.

## Target State

The production target is a review-first document workflow:

- Users and clients upload bills, invoices, receipts, bank statements, and supporting documents into a tenant-scoped inbox.
- Storage uses a configured private object-storage provider with tenant-scoped keys, signed download access, retention controls, and audit logging.
- OCR or AI extraction may create draft suggestions for party, amount, tax, due date, bank line, voucher, or account categorization fields.
- Human users must review, correct, and explicitly approve any generated accounting document or journal posting.
- OCR and AI outputs must never auto-post to the ledger, file statutory returns, mutate locked records, or bypass role/module permissions.

## Required Provider Controls

Before enabling OCR or external document providers for a production tenant:

- Tenant policy must authorize external processing for uploaded documents.
- Provider credentials must be server-side only and must not be exposed to frontend code.
- Uploads must be screened for file type, size, and malware before provider handoff.
- Provider requests must include only the minimum document and metadata needed for extraction.
- Provider responses must be stored according to tenant retention policy and marked as machine-generated suggestions.
- Every extraction, suggestion acceptance, rejection, download, and posting action must be audited with actor, tenant, app key, source document, and timestamp.
- Failure modes must leave the document in a reviewable state without marking the business transaction complete.

## Gap

The local inbox workflow is implemented, but production readiness is not complete. Open work remains for:

- Real-stack/demo mutation against a clearly marked demo tenant.
- Object-storage provider selection and environment configuration.
- Malware scanning and stricter file-type validation.
- OCR/provider integration contract, retention policy, and tenant authorization controls.
- Production signoff for audit retention, backup/restore, and rollback expectations.

## Deferred Scope

The following remain deferred until the deterministic document workflow and provider controls pass review:

- OCR/AI auto-extraction in production.
- Suggested account allocation driven by external AI providers.
- Auto-posting from OCR or AI output.
- Direct statutory filing from uploaded documents.
- External provider processing of confidential tenant documents without tenant authorization.

