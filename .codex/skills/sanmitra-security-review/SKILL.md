---
name: sanmitra-security-review
description: SanMitra security and privacy review workflow for auth, tenant context, RBAC, app-key handling, module access, LegalMitra confidentiality, secrets, logging, uploads, external providers, payments, accounting data, or any change with tenant/security risk.
---

# SanMitra Security Review

## Authority

- Treat `AGENTS.md` as mandatory policy and source of truth.
- Load `tenant-context-routing` for auth, tenant, app-key, module, RBAC, or protected query changes.
- Load `legalmitra-compliance` for LegalMitra data, RAG, providers, documents, drafts, or compliance workflows.
- Load `accounting-doctrine` for payments, receipts, collections, postings, reports, or money-bearing workflows.
- Load `migration-safety` for schema, index, seed, or backfill changes.

## Threat Focus

1. Identify the protected asset: tenant data, legal data, accounting records, credentials, PII, payment data, broker data, or operational metadata.
2. Identify the trust boundary: request headers, token claims, tenant override, app key, role, provider call, database query, upload, export, or background job.
3. Check the allow/deny path for unauthorized, cross-tenant, cross-app, inactive-tenant, and disabled-module access.
4. Check failure modes: provider outage, partial write, malformed token, missing app key, missing tenant, stale permission, duplicate request, or logging leak.

## Checklist

- Do not accept tokens in request bodies.
- Do not trust `tenant_id` from request body for protected routes.
- Treat `X-Tenant-ID` as super-admin-only override when implemented, and require auditability.
- Validate `X-App-Key` and fail gracefully when missing or invalid.
- Scope every tenant-owned MongoDB query and PostgreSQL accounting query.
- Do not log passwords, tokens, payment data, legal documents, broker credentials, PII exports, or database dumps.
- Do not send confidential legal tenant documents to external providers without tenant policy and user authorization.
- Keep secrets out of code, tests, docs, fixtures, logs, and committed artifacts.

## Output

- Report exploitable or policy-breaking issues first.
- Include exact file and line references when available.
- Label critical risks with `[CRITICAL-TENANCY]`, `[CRITICAL-LEGAL]`, `[CRITICAL-ACCOUNTING]`, `[CRITICAL-PAYMENT]`, `[CRITICAL-INVESTMENT]`, or `[CRITICAL-SECURITY]` where appropriate.
- If no issue is found, state the residual risk and what was not tested.
