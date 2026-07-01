# MitraBooks Completion Roadmap

## Current State

MitraBooks has working business-accounting slices for parties, vouchers, invoices, bills, credit/debit notes, GST preparation, TDS/TCS, statements, bank reconciliation, inventory basics, fixed assets, dimensions, opening balances, year-end close, audit trails, and financial health checks.

Current implementation classification:

- Implemented but not production-ready: typed vouchers, sales invoices, purchase bills, credit/debit notes, GST settlement, statements, bank reconciliation, fixed assets, dimensions, inventory basics, opening balances, and year-end close.
- Implemented: cross-store compensation/reversal protection for payroll, bulk import, typed vouchers, sales invoices, purchase bills, credit notes, debit notes, and GST settlement.
- Implemented locally: CA invite backend hardening now uses token-based invite acceptance with expiry, single-use acceptance, and revoke handling; the public invite-accept UX and browser coverage are in place.
- Implemented but not production-ready: core settings backend contracts, CA practice client master/document queue/company switching, tenant-scoped document attachments, and tenant-scoped integration/AI configuration shells.
- Planned/deferred: browser E2E depth beyond local smoke/preflight, compliance signoff, export governance, Data Health Score, advanced inventory depth, and deeper multi-client CA practice modeling.

The landing page, public legal pages, pricing content, and backend MitraBooks pricing catalog are in place.

The settings screen now saves tenant-scoped core business settings plus integration/AI configuration shells. It still should not pretend that provider secrets, live filing, live bank execution, OCR auto-posting, or compliance certification are complete before those are implemented and tested.

## Immediate Work Plan

| Phase | Dates | Scope | Completion Definition |
| --- | --- | --- | --- |
| Phase 1 closeout | 2026-06-24 to 2026-07-01 | High-risk correctness and security hardening: compensation pattern across business posting flows, true invoice/bill draft-to-approve lifecycle, posted-only invoice output guard, and CA token-based invite acceptance | Cross-store posting flows reverse automatically on post-persist failure, invoices/bills no longer auto-post on create, CA invites no longer expose or rely on temporary passwords, public invite acceptance has browser coverage, and local frontend preflight passes |
| Phase 2A | 2026-06-12 to 2026-06-14 | Landing page pricing polish, separate regular-business and CA/bookkeeper pricing, LegalMitra/MandirMitra/GruhaMitra/MitraBooks shared Razorpay account configuration, and billing metadata capture | Pricing is visible, all four product pricing endpoints exist, MitraBooks business and CA practice pricing are separate, Razorpay config uses the SanMitra account env, and webhook transactions record app/plan metadata |
| Phase 2B | 2026-06-15 to 2026-06-21 | Core settings backend contracts: organization profile, branches, roles, permissions, voucher numbering, financial locks, templates, notifications | Implemented locally: settings cards now save tenant-scoped business admin settings through `/api/v1/business/admin-settings` |
| Phase 2C | 2026-06-22 to 2026-06-30 | CA practice onboarding: client master, multi-company dashboard, client access controls, compliance tracking, and work assignment | Implemented locally: CA Practice Portal now supports tenant-safe client records, staff assignment, document review queues, and company switching |
| Phase 2D | 2026-07-01 to 2026-07-12 | Integrations and automation: payment gateway mapping, document storage, OCR pipeline, AI settings, GST/bank/WhatsApp/email configuration shells | Implemented locally as review-first config shells: integrations are tenant-configurable, provider secrets are not exposed to the frontend, and AI/OCR auto-posting remains disabled |
| Phase 2E | 2026-07-13 to 2026-07-19 | Browser E2E, accounting guardrail checks, tenant/app isolation checks, staging deployment validation | Local route tests and frontend smoke/preflight must pass; staging validation remains a separate signoff step before production claims |

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
RAZORPAY_ACCOUNT_OWNER=Sanmita Tech Solutions
RAZORPAY_MERCHANT_SCOPE=sanmitra_platform
RAZORPAY_PAYMENT_PAGE_MAP_JSON
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

## MitraBooks Pricing Direction

Regular business account pricing and CA Practice / Bookkeeper pricing must stay separate.

### Regular Business Account

| Plan | Monthly | Yearly | Business scope | Users | OCR documents |
| --- | ---: | ---: | --- | ---: | ---: |
| Free | Rs. 0 | Rs. 0 | 1 company | 1 | 0 |
| Basic | Rs. 499 | Rs. 4,999 | 1 company | 3 | 25 |
| Starter | Rs. 999 | Rs. 9,999 | 2 branches | 5 | 25 |
| Growth | Rs. 1,499 | Rs. 14,999 | 5 branches | 10 | 100 |
| Enterprise | Get quote | Get quote | 1 company, multi-branch custom scope | Multi-user | Custom documents / AI MIS by requirement |

### CA Practice / Bookkeepers

| Plan | Monthly | Yearly | Client companies | Practice users | OCR documents |
| --- | ---: | ---: | ---: | ---: | ---: |
| Basic | Rs. 499 | Rs. 4,999 | 5 | 1 | 0 |
| Starter | Rs. 999 | Rs. 9,999 | 25 | 5 | 500 |
| Growth | Rs. 2,999 | Rs. 29,999 | 50 | 15 | Unlimited subject to fair-use |

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

## Immediate Remaining Gaps After Phase 1 Closeout

- Approval workflow depth beyond invoices and bills is still implemented but not complete as one uniform lifecycle across every ERP document.
- Browser E2E for invoice, bill, reconciliation, inventory, fixed-asset, and settings workflows still needs deeper coverage beyond local smoke/preflight.
- Compliance signoff for GST/TDS remains pending and should stay labeled preparation/reporting until reviewed.
- Export governance, Data Health Score, advanced inventory, and deeper multi-client CA practice modeling remain planned/deferred.
