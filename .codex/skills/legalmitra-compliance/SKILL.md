---
name: legalmitra-compliance
description: LegalMitra safety workflow for legal cases, matters, documents, templates, notices, contracts, legal research, RAG, compliance calendar, Claude Legal Counsel/provider integrations, tenant confidentiality, legal-source attribution, deadline/versioning controls, and human-review gates. Use whenever changing LegalMitra backend, frontend, AI, retrieval, document, template, or compatibility behavior.
---

# LegalMitra Compliance

## Workflow

1. Classify the change: case/matter, document/template, research/RAG, provider integration, billing, deadline, or compatibility API.
2. Confirm tenant and app isolation before reading or returning legal data.
3. Preserve human-review status for generated legal drafts.
4. Preserve source attribution for legal research and retrieval output.
5. Keep provider failures safe: no fabricated citations, no silent confidential data leakage, no production enablement without policy checks.

## AI And Research Rules

- Never present generated content as final legal advice.
- Generated legal content should remain draft/advisory until reviewed by an authorized user.
- Do not allow generated documents to be sent, filed, or published without review state and actor metadata where the workflow supports it.
- Never hallucinate case numbers, statute sections, court names, or citations.
- Include source attribution and retrieval/source dates for legal research where data can change.
- Require jurisdiction to be explicit where legal rules differ.
- Jurisdiction-specific legal rules should be configurable, not hard-coded.

## Confidentiality And Provider Rules

- Do not send confidential tenant documents to external providers unless tenant policy and user authorization permit it.
- Do not store prompts/responses beyond tenant retention and confidentiality policy.
- Provider fallback must fail safely without fabricated legal authority.
- Compatibility APIs that expose tenant data must be authenticated and must resolve tenant from trusted context.

## Data Expectations

Legal matters/cases should usually include:

- `tenant_id`
- matter/client references
- matter type and status
- jurisdiction/court where applicable
- assigned user/team
- created/updated actor metadata

Legal documents and generated drafts should usually include:

- `tenant_id`
- matter/client/document reference
- document type, jurisdiction, and language where applicable
- status and version/revision
- parent version or revision chain where supported
- AI-generated flag and human-review state where applicable
- created/reviewed actor metadata
- retention/audit metadata

## Versioning And Deadlines

- Legal document edits should preserve version history.
- Executed/filed documents should be locked or require explicit audited unlock.
- Deletes should be soft/archive operations unless the retention policy explicitly requires erasure.
- Hearing dates, limitation dates, compliance dates, and reminders must be tenant-scoped and auditable.
- Missed limitation dates should alert or audit; they must not silently disappear.

## Completion Checklist

- Confirm no unauthenticated tenant-private legal data path exists.
- Confirm cross-tenant header/body override is rejected unless super-admin gated.
- Confirm generated legal output is draft/advisory with human review.
- Confirm source attribution remains intact for research/RAG.
- Confirm jurisdiction is explicit or blocked until confirmed.
- Confirm versioning/deadline/audit behavior is preserved.
- Add tests for auth, tenant isolation, provider fallback, source attribution, or review gates where practical.
