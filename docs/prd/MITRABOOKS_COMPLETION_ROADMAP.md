# MitraBooks Completion Roadmap

## Current State

MitraBooks has working business-accounting slices for parties, vouchers, invoices, bills, credit/debit notes, GST preparation, TDS/TCS, statements, bank reconciliation, inventory basics, fixed assets, dimensions, opening balances, year-end close, audit trails, and financial health checks.

The landing page, public legal pages, pricing content, and backend MitraBooks pricing catalog are in place.

The settings screen intentionally shows several items as planned because the UI should not pretend that backend contracts, external integrations, or high-risk accounting controls are complete before they are implemented and tested.

## Immediate Work Plan

| Phase | Dates | Scope | Completion Definition |
| --- | --- | --- | --- |
| Phase 2A | 2026-06-12 to 2026-06-14 | Landing page pricing polish, LegalMitra/MandirMitra/GruhaMitra/MitraBooks shared Razorpay account configuration, and billing metadata capture | Pricing is visible, all four product pricing endpoints exist, Razorpay config uses the SanMitra account env, and webhook transactions record app/plan metadata |
| Phase 2B | 2026-06-15 to 2026-06-21 | Core settings backend contracts: organization profile, branches, roles, permissions, voucher numbering, financial locks, templates, notifications | Settings cards stop saying only "Needs Backend Contract" and either save tenant-scoped settings or route to implemented workspaces |
| Phase 2C | 2026-06-22 to 2026-06-30 | CA practice onboarding: client master, multi-company dashboard, client access controls, compliance tracking, and work assignment | CA Practice Portal supports tenant-safe client records, staff assignment, document review queues, and company switching |
| Phase 2D | 2026-07-01 to 2026-07-12 | Integrations and automation: payment gateway mapping, document storage, OCR pipeline, AI settings, GST/bank/WhatsApp/email configuration shells | Integrations are tenant-configurable, secrets are not exposed to the frontend, and AI/OCR remains review-first |
| Phase 2E | 2026-07-13 to 2026-07-19 | Browser E2E, accounting guardrail checks, tenant/app isolation checks, staging deployment validation | MitraBooks ERP core, CA practice, landing, pricing, and billing smoke/E2E pass on staging |

## Razorpay Direction

All four products should use one SanMitra Technologies Razorpay account:

- LegalMitra
- MandirMitra
- GruhaMitra
- MitraBooks

Runtime configuration must come from environment variables:

```text
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
RAZORPAY_ACCOUNT_OWNER=SanMitra Technologies Private Limited
RAZORPAY_MERCHANT_SCOPE=sanmitra_platform
```

Razorpay notes should include:

```json
{
  "app_key": "mitrabooks",
  "plan": "growth",
  "tenant_id": "tenant-id-if-available"
}
```

Do not commit Razorpay secrets.

## Planned Settings Breakdown

### Phase 2B

- Organization settings
- Branch settings
- Users and roles
- Permissions
- Voucher numbering and approval matrix
- Security settings
- Templates
- Notifications
- Subscription and billing settings

### Phase 2C

- Client management
- Multi-company dashboard
- Client access control
- Compliance tracking
- Work assignment

### Phase 2D

- Payment gateway mapping
- GST portal integration settings
- Bank API settings
- WhatsApp and email provider settings
- Document storage
- OCR extraction controls
- AI settings

## Non-Goals For This Sequence

- Do not auto-post AI/OCR outputs to the ledger.
- Do not store payment card details or Razorpay secrets in tenant records.
- Do not bypass tenant/app-key checks for CA practice client switching.
- Do not enable live GST filing or bank payment execution until provider contracts, tenant authorization, and E2E checks are complete.
