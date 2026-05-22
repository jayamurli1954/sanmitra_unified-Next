# MandirMitra First Live Cut Decisions

Date: 2026-05-22

This document records the scope decision for making MandirMitra live inside the MitraBooks ERP shell.

## Live Cut Scope

### Included In First Live Cut

| Area | Decision | Evidence |
| --- | --- | --- |
| Donations | Include | Receipt generation, Kannada/English receipt text, public payment verification, and accounting posting are covered by smoke/tests. |
| Sponsorship accounting | Include | Cash sponsorships post as sponsorship income; valued in-kind sponsorships post dynamically to expense or inventory based on temple inventory setting, with precious articles posted to temple assets. |
| Sevas | Include | Booking, receipt generation, Kannada/English receipt text, and accounting posting are covered by smoke/tests. |
| Expenses | Include | Quick expense posts through MandirMitra accounting and reconciles in reports. |
| Public payments | Include | No-login public payment submission, correction, rejection, staff verification, and audit trace are covered locally. |
| Receipts | Include | Donation/seva receipt preview/download and receipt-history workspace are wired. |
| Panchang | Include | ERP shell renders `/api/v1/panchang/today` for the active temple tenant. |
| Reports | Include | Donation category, detailed donation, detailed seva, seva schedule, and recent devotee reports are wired. |
| Accounting reports | Include | Trial Balance, Income & Expenditure, Receipts & Payments, Balance Sheet, drill-down, and voucher detail are verified. |

### Deferred From First Live Cut

| Area | Decision | Reason |
| --- | --- | --- |
| Hundi collections | Defer | Current backend has placeholder Hundi endpoints and `module_hundi_enabled` defaults to false. Do not expose as live until collection entry, counting, deposit, receipt/accounting rules, and audit tests exist. |
| Festival/fund workflows | Defer | Sevas can mark festival-only availability, but full festival/fund accounting and corpus/fund-specific reporting are not complete enough for live signoff. |
| Receipt cancellation/refund UI | Defer | Generic Mandir journal cancellation/reversal exists, but donation/seva receipt-domain cancellation and refund policy need explicit linked domain records, reversal journal reference, audit event, and tests. |
| 80G/FCRA issuance | Defer | Must be tenant-configured and compliance-reviewed. Do not default eligibility to true or print/claim 80G/FCRA treatment until tenant configuration, registration fields, receipt text, and tests exist. |

## Non-Negotiable Gates For Deferred Scope

### Hundi

Before enabling Hundi live:

- `module_hundi_enabled` must remain tenant-configured and default false.
- Hundi count/deposit entries must post through MitraBooks accounting.
- Cash-in-hundi and bank-deposit flows must not duplicate income.
- Every count/deposit must retain actor, date, amount, location/hundi box, and audit trail.
- Trial Balance and Receipts & Payments must reconcile after Hundi postings.

### Festival And Fund Accounting

Before enabling festival/fund live:

- Funds must map to tenant-specific accounting treatment.
- Corpus/restricted funds must not silently flow to general donations.
- Festival collections and expenses must be reportable by festival/fund.
- Fund transfer or reclassification must use journal entries with actor and approval metadata.

### Sponsorship And In-Kind Donation Accounting

Sponsorship and valued in-kind donations are included in the first live cut only at the accounting-posting level.

- Cash sponsorship for Annadanam, flower decoration, lighting, festival, vastra, or similar event support must debit cash/bank and credit Sponsorship Income.
- Valued in-kind sponsorship for Annadanam consumables such as rice, dal, oil, ghee, or food must debit Prasadam Expenses when inventory accounting is disabled and Prasadam Inventory when inventory accounting is enabled, with credit to In-Kind Sponsorship Income.
- Valued in-kind sponsorship that is directly consumed for flowers, decoration, lighting, festival, event, or service support must debit the relevant expense bucket and credit In-Kind Sponsorship Income.
- Precious articles such as gold, silver, ornaments, idols, or ritual articles must debit the appropriate temple asset account and credit In-Kind Donation Income or In-Kind Sponsorship Income depending on purpose.
- Inventory accounting is tenant-configured through the temple module setting; small temples can keep inventory off and expense consumable in-kind receipts immediately.
- The ERP quick-entry donation form may capture cash/in-kind type, event/festival, item name, item type, quantity, and valuation basis for operational traceability.
- Zero-value in-kind acknowledgements may remain memo/domain records only and must not create a GL entry until a valuation is recorded.
- Rich event/fund subledger reporting, stock issue/consumption, and restricted-fund reporting remain part of the festival/fund deferred scope above.

### Cancellation And Refund

Before enabling receipt cancellation/refund live:

- Issued receipt records must remain immutable and be marked cancelled/reversed instead of edited.
- The original journal must not be changed in place.
- Reversal or adjustment journal must link to the original source document.
- Refund payment mode, refund date, actor, reason, and approval metadata must be recorded.
- Duplicate cancellation/refund requests must be idempotent.

### 80G/FCRA

Before enabling 80G/FCRA live:

- Eligibility must come from tenant/trust configuration.
- Registration number, effective date, expiry/validity, and receipt text must be stored per tenant.
- FCRA-related donations must be separately identified and reportable.
- Receipts must not claim 80G/FCRA status unless the tenant configuration allows it for that donation category/date.

## Release Recommendation

MandirMitra first live cut can proceed for donation, seva, public payment, receipt, Panchang, reports, and accounting workflows after CI/staging pass.

The deferred areas above must remain hidden, disabled, or clearly marked not-live until their gates are implemented and tested.
