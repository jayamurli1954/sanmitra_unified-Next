---
name: mandirmitra-admin
description: MandirMitra temple, trust, NGO, donation, receipt, seva, devotee, festival, fund, 80G/FCRA-readiness, and temple accounting workflow. Use when changing MandirMitra backend, frontend, compatibility APIs, donation/seva posting, receipt generation, devotee records, trust compliance, or MandirMitra integration with MitraBooks accounting.
---

# MandirMitra Administration

## Domain Overview

MandirMitra manages temple/trust operations:

- donations and hundi collections
- receipts and numbering
- seva booking and scheduling
- devotees and donor records
- festivals, events, puja schedules, and prasad workflows
- trust/corpus/fund accounting
- 80G and FCRA readiness where tenant configuration supports it

Use `organization_type = TEMPLE` and app key `mandirmitra` where compatibility requires it.

## Donation And Receipt Rules

- Every donation must generate a stable, tenant-scoped receipt number.
- Issued receipts are immutable; corrections require cancellation/reversal and a new receipt.
- 80G eligibility must come from tenant/trust configuration and must not default to true.
- Cash donation PAN/threshold rules must be configurable by jurisdiction/effective date.
- Anonymous donations must not retain unnecessary PII.
- Earmarked donations must track the designated fund/corpus and must not silently flow to general operations.
- Do not hard-code country/currency unless tenant configuration requires it.

## Seva Rules

- Seva bookings must be tenant-scoped and linked to devotee/customer context where available.
- Payment state and booking state must be separate.
- Refunds/cancellations must preserve audit trail.
- Seva collections must post through MitraBooks accounting when financially recognized.

## Accounting Integration

- Donation and seva collections post through the shared accounting service.
- MandirMitra must never write directly to ledger tables.
- Typical donation posting: debit cash/bank, credit donation income or fund-specific income.
- Typical seva posting: debit cash/bank, credit seva income.
- Refunds and receipt cancellations must reverse or adjust the original accounting entry.
- Financial posting failure must not leave a completed-looking domain transaction.

## Fund And Trust Controls

- Funds such as renovation, annadanam, corpus, or specific festival funds need separate accounting/reporting treatment.
- Fund transfers require journal entries and actor/approval metadata.
- Annual income/expense reports should derive from posted accounting entries.
- FCRA-related fields, if enabled, must be tenant-configured and reported separately.

## Devotee Privacy

- Devotee PII must be tenant-scoped and role-gated.
- Do not log PAN, phone, email, payment references, or sensitive devotee details.
- Support soft-delete/anonymization patterns where policy requires it.

## Completion Checklist

- Confirm donation receipt generation cannot be skipped.
- Confirm receipt numbering is tenant-scoped, stable, and auditable.
- Confirm 80G/FCRA behavior is tenant-configured, not hard-coded.
- Confirm donation/seva financial effects go through MitraBooks accounting.
- Confirm cancellation/refund behavior reverses or adjusts accounting safely.
- Confirm devotee PII is access-controlled and not logged.
- Add tests for receipt immutability, tenant isolation, posting failure, fund accounting, and receipt cancellation where practical.
