# MitraBooks Feature and Pricing Verification Checklist

Date: 2026-06-14

Purpose: map MitraBooks business and CA/bookkeeper features against verification status and pricing tiers before publishing final pricing, payment pages, or sales promises.

This checklist distinguishes current implementation evidence from target product positioning. It should be updated after each backend test, browser E2E pass, staging smoke, and pricing-page change.

## Status Legend

| Status | Meaning |
| --- | --- |
| Working | Current docs/tests/smoke evidence indicate the feature is usable and verified at least at the relevant workflow level. |
| Partially working | Backend/UI slice exists or is documented as implemented, but browser E2E, compliance review, approval depth, or production-hardening is still pending. |
| Available / needs verification | Existing docs claim or describe the feature, but this checklist has not independently verified it in the current turn. |
| Planned / configuration-dependent | Feature depends on later module work, provider configuration, tenant authorization, or custom scope. |
| Not included | Should not be promised in that plan. |

## Current Local Browser Evidence

Date: 2026-06-14

Command:

```powershell
cd frontend
npx.cmd playwright test e2e/mitrabooks-shell.spec.js --project=chromium
```

Result:

```text
3 passed
```

Verified in the local built/static MitraBooks ERP shell:

- Login validation and password visibility toggle.
- Stale cached token fails closed and returns to sign-in.
- Authenticated business dashboard shell with mocked tenant/module context.
- Main navigation groups and enabled Bills workspace.
- Party master route, New Party action, create, edit, and soft deactivate from the active list.
- Voucher route, New Voucher dialog, debit/credit line rendering, account selectors, imbalance state, disabled submit for an unbalanced voucher, balanced journal posting, and voucher reversal.
- Accounting drill-down route.
- Sales invoice route, New Invoice form, GST total preview, posting, list row, detail view, and reversal panel.
- Purchase bill route, New Bill form, input GST total preview, posting, list row, detail view, and reversal panel.
- Credit note route, New Credit Note form, GST total preview, posting, list row, detail view, and reversal panel.
- Debit note route, New Debit Note form, input GST total preview, posting, list row, detail view, and reversal panel.
- Enabled route availability for Sales Invoices, Purchase Bills, Credit Notes, Debit Notes, Financial Reports, GST Returns, Reconciliation, TDS/TCS, Bank Reconciliation, Financial Health, and MitraBooks Settings.

Limitations:

- This is frontend shell/workspace verification with mocked backend responses.
- It does not prove live backend posting, GST/TDS compliance correctness, report totals, tenant isolation, entitlement enforcement, or production data safety.
- Keep tax/banking/compliance-depth workflows marked `Partially working` until safe backend E2E proves create -> post -> report -> reverse behavior.
- Party master and journal-voucher rows can now be treated as locally verified because backend tests and browser E2E both cover the relevant workflow.
- Core sales invoice and purchase bill lifecycle rows can now be treated as locally verified because backend tests cover posting/reversal and browser E2E covers the user-facing create/detail/reverse paths.
- Core credit note and debit note lifecycle rows can now be treated as locally verified because backend tests cover posting/reversal and browser E2E covers the user-facing create/detail/reverse paths.

## Pricing Tracks

MitraBooks has two pricing tracks and they should stay separate.

### Regular Business

| Plan | Monthly | Yearly | Companies | Users | OCR / AI documents | Commercial role |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Free | INR 0 | INR 0 | 1 | 1 | 0/month | Trial and very small manual-entry businesses. |
| Basic | INR 499 | INR 4,999 | 1 | 1 | 25/month | Single-user business with GST/TDS prep and basic reports. |
| Starter | INR 999 | INR 9,999 | 5 | 1 | 25/month | Growing business or single-user multi-company use. |
| Growth | INR 1,499 | INR 14,999 | 10 | 1 | 100/month | Larger single-user business with higher document limits and assistance features. |

### CA Practice / Bookkeeper

| Plan | Monthly | Yearly | Client companies | Practice users | OCR / AI documents | Commercial role |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Basic | INR 499 | INR 4,999 | 5 | 1 | 0/month | Single practitioner with manual multi-company tracking. |
| Starter | INR 999 | INR 9,999 | 25 | 5 | 500/month | Small team with client document queues and work assignment. |
| Growth | INR 2,999 | INR 29,999 | 50 | 15 | Fair-use unlimited | Larger practice workspace with priority support and onboarding review. |

## Regular Business Matrix

| Feature area | Feature | Current status | Free | Basic | Starter | Growth | Evidence / next verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accounting core | Tenant-scoped chart of accounts | Working | Included | Included | Included | Included | Gap matrix says shared accounting engine and COA foundation exist; verify business-type template selection before public onboarding. |
| Accounting core | Journal posting through accounting service | Working | Included | Included | Included | Included | Shared accounting engine supports posting, reversal, idempotency, and reports. Must remain service-layer only. |
| Accounting core | Journal reversal | Working | Included | Included | Included | Included | Gap matrix states reversal support exists. Verify UI reversal flow per business document. |
| Accounting core | Idempotent posting | Working | Included | Included | Included | Included | Existing accounting guardrails require idempotency; keep focused tests in CI. |
| Accounting reports | Ledger | Working | Included | Included | Included | Included | Shared ledger reports exist. MitraBooks shell route smoke now covers accounting drill-down and financial reports; live business-tenant totals still need backend E2E. |
| Accounting reports | Trial balance | Working | Included | Included | Included | Included | Shared trial balance exists and has MandirMitra smoke evidence. MitraBooks shell route smoke covers Financial Reports/Trial Balance visibility; live business E2E remains pending. |
| Accounting reports | Profit and loss / income statement | Working | Included | Included | Included | Included | Gap matrix lists P&L. MitraBooks reports route is browser-smoked; verify business tenant totals and naming with posted data. |
| Accounting reports | Receipts and payments | Working | Included | Included | Included | Included | Shared report exists. Verify business tenant data and exports. |
| Accounting reports | Balance sheet | Working | Included | Included | Included | Included | Shared report exists. Verify with posted business vouchers/invoices. |
| Business master | Party/customer/vendor master | Working | Included | Included | Included | Included | Backend tests cover tenant/app scope, ledger-derived balances, update without balance mutation, and soft deactivate. Browser smoke verifies create, edit, and deactivate from the active list. |
| Business master | Party profile update without balance mutation | Working | Included | Included | Included | Included | Previous fix cycle clarified party balances must be ledger-derived, not directly edited. |
| Vouchers | Payment voucher | Partially working | Included | Included | Included | Included | Typed voucher API exists and posts via accounting. Browser smoke verifies voucher route, New Voucher dialog, debit/credit lines, account selectors, imbalance state, and disabled submit. Posting E2E and keyboard UX polish pending. |
| Vouchers | Receipt voucher | Partially working | Included | Included | Included | Included | Browser smoke verifies receipt voucher line labels and imbalance guard. Verify AR allocation and successful posting where applicable. |
| Vouchers | Contra voucher | Partially working | Included | Included | Included | Included | Same typed voucher route. Verify bank/cash transfer reports and successful posting. |
| Vouchers | Journal voucher | Working | Included | Included | Included | Included | Backend smoke covers journal posting, debit-credit equality, route detail, drill-down, and reversal. Browser smoke covers unbalanced UI guard, balanced journal posting, and visible reversal state. |
| Vouchers | Voucher numbering | Partially working | Included | Included | Included | Included | Generated voucher numbers exist; settings/backend contract depth planned in Phase 2B. |
| Vouchers | Voucher reversal UX | Working | Included | Included | Included | Included | Backend smoke verifies reversal journal links and opposite debit/credit lines. Browser smoke verifies the Reverse action and reversed row state. Approval/period-lock policy is still a separate settings/control item. |
| Sales | Sales invoices | Working | Included | Included | Included | Included | Backend tests cover posted sales invoice accounting and reversal. Browser smoke verifies New Invoice form, totals preview, posting, list row, detail view, and reversal panel. Approvals and print/export polish remain separate planned/partial scope. |
| Sales | GST/TCS on sales | Partially working | Not included | Included | Included | Included | Implemented slices exist; compliance review and effective-date tax configuration still needed. |
| Sales | Invoice cancellation reversal | Working | Included | Included | Included | Included | Backend tests verify GL reversal for posted invoices. Browser smoke verifies the reversal panel and reversed status display. Audit-log review remains separate. |
| Purchases | Purchase bills | Working | Included | Included | Included | Included | Backend tests cover posted purchase bill accounting and reversal. Browser smoke verifies New Bill form, input GST totals preview, posting, list row, detail view, and reversal panel. Approval/document support remains separate partial/planned scope. |
| Purchases | ITC/RCM/TDS entries | Partially working | Not included | Included | Included | Included | Implemented slices exist; compliance review pending. |
| Notes | Credit notes | Working | Included | Included | Included | Included | Backend tests cover credit note posting as the mirror of an invoice and cancellation through reversing journal entry. Browser smoke verifies New Credit Note form, GST total preview, posting, list row, detail view, and reversal panel. Strict source-invoice linkage remains a separate control/compliance item. |
| Notes | Debit notes | Working | Included | Included | Included | Included | Backend tests cover debit note posting as the mirror of a bill and cancellation through reversing journal entry. Browser smoke verifies New Debit Note form, input GST total preview, posting, list row, detail view, and reversal panel. Strict source-bill linkage remains a separate control/compliance item. |
| GST | GST profile/setup basics | Partially working | Not included | Included | Included | Included | GSTIN/place-of-supply/HSN/SAC basics exist; tenant GST profile UX and compliance review pending. |
| GST | GSTR-1 preparation | Partially working | Not included | Included | Included | Included | Implemented preparation report and GST Returns route is browser-smoked; do not call it production filing. |
| GST | GSTR-3B preparation | Partially working | Not included | Included | Included | Included | Implemented preparation report and GST Returns route is browser-smoked; reconcile to posted invoices/journals before sales claims. |
| GST | GSTR-2B reconciliation | Partially working | Not included | Not included | Included | Included | Implemented slice; browser E2E and compliance signoff pending. |
| GST | CMP-08 / GSTR-4 | Partially working | Not included | Not included | Included where applicable | Included where applicable | Composition-related reporting exists; only promise when tenant classification requires it. |
| GST | Live GST filing | Planned / configuration-dependent | Not included | Not included | Not included | Optional/custom later | Explicit non-goal until provider contracts, tenant authorization, and compliance review pass. |
| E-invoice / e-way | Readiness view and manual IRN | Partially working | Not included | Not included | Included where applicable | Included where applicable | E-invoice readiness and manual IRN exist; live IRP/e-way APIs are deferred. |
| TDS/TCS | TDS/TCS tracking | Partially working | Not included | Included | Included | Included | Implemented slices exist and TDS/TCS route is browser-smoked; compliance review and tenant settings depth pending. |
| Receivables | Customer statements | Partially working | Not included | Included | Included | Included | Implemented; browser E2E pending. |
| Receivables | Open-item allocation | Partially working | Not included | Not included | Included | Included | Implemented; verify FIFO suggestions and manual allocation. |
| Receivables | Ageing | Partially working | Not included | Included | Included | Included | Implemented; browser E2E pending. |
| Payables | Vendor statements | Partially working | Not included | Included | Included | Included | Implemented; browser E2E pending. |
| Payables | Payable ageing | Partially working | Not included | Included | Included | Included | Implemented; browser E2E pending. |
| Banking | Manual bank reconciliation | Partially working | Not included | Not included | Included | Included | Implemented CSV import/matching/reversal/summary and Bank Reconciliation route is browser-smoked; import/match/reverse E2E pending. |
| Banking | Bank book / cash book polish | Planned / configuration-dependent | Not included | Not included | Included | Included | Gap matrix calls for polish. |
| Banking | Bank API sync | Planned / configuration-dependent | Not included | Not included | Not included | Optional/custom later | Deferred; do not promise live bank execution. |
| Inventory | Item master and basic stock register | Partially working | Not included | Not included | Included | Included | Implemented opt-in inventory basics; valuation policy settings and E2E pending. |
| Inventory | Closing-stock journal posting | Partially working | Not included | Not included | Included | Included | Implemented weighted-average closing stock journal posting; verify tenant setting and report impact. |
| Inventory | Batch/serial/multi-location | Planned / configuration-dependent | Not included | Not included | Not included | Optional/custom later | Deferred until basic inventory passes E2E. |
| Fixed assets | Fixed asset register | Partially working | Not included | Not included | Included | Included | Implemented; disposal workflow and browser E2E pending. |
| Fixed assets | Depreciation preview/posting | Partially working | Not included | Not included | Included | Included | Implemented SLM/WDV preview and depreciation journal posting; compliance review pending. |
| Dimensions | Cost centre / project master | Partially working | Not included | Not included | Included | Included | Implemented dimensions and income/expense/net reports; tagging coverage needs E2E. |
| Migration | Opening balance import/posting | Partially working | Not included | Included where needed | Included | Included | Implemented controlled journal flow; maker-checker and rollback examples pending. |
| Year end | Year-end close preview/posting | Partially working | Not included | Not included | Included | Included | Implemented; maker-checker and browser E2E pending. |
| MIS | Financial health summary | Partially working | Included basic | Included | Included | Included | Financial Health route is browser-smoked with mocked ledger-backed payload; deterministic MIS expansion and live report validation still planned. |
| MIS | Sales/purchase trends, top parties, working capital | Planned / configuration-dependent | Not included | Not included | Included where implemented | Included | Phase 5 expansion. |
| Data health | Data Health Score | Planned / configuration-dependent | Not included | Not included | Not included | Planned | Useful product idea, not current promise. |
| Exports | PDF/Excel/JSON exports | Planned / configuration-dependent | Limited where implemented | Included where implemented | Included where implemented | Included where implemented | Define export permissions, audit, and exact formats before public claims. |
| Exports | Tally XML export | Planned / configuration-dependent | Not included | Not included | Not included | Planned/custom | Preserve as target, not first-release promise. |
| Settings | Organization profile/settings | Partially working | Included | Included | Included | Included | Settings UI exists and MitraBooks Settings route is browser-smoked; Phase 2B adds backend contracts. |
| Settings | Branch settings | Planned / configuration-dependent | Not included | Included where applicable | Included | Included | Phase 2B. |
| Settings | Roles and permissions | Planned / configuration-dependent | Not included | Basic | Included | Included | Phase 2B. Must enforce backend RBAC, not only UI hiding. |
| Settings | Financial locks | Planned / configuration-dependent | Not included | Included | Included | Included | Phase 2B. Important before production GST/accounting claims. |
| Settings | Templates and notifications | Planned / configuration-dependent | Not included | Included where enabled | Included | Included | Phase 2B/2D. |
| OCR / AI | Document upload queue | Planned / configuration-dependent | Not included | Basic planned | Included planned | Included planned | Planned after deterministic document workflow. Do not promise as working. |
| OCR / AI | OCR extraction | Planned / configuration-dependent | Not included | 25/month planned | 25/month planned | 100/month planned | Pricing docs mention limits, but implementation needs verification before publishing. |
| OCR / AI | AI categorization suggestions | Planned / configuration-dependent | Not included | Not included | Planned | Planned | Human review required before posting. |
| OCR / AI | AI auto-posting | Not included | Not included | Not included | Not included | Not included | Forbidden. AI/OCR must never post directly. |

## CA Practice / Bookkeeper Matrix

| Feature area | Feature | Current status | CA Basic | CA Starter | CA Growth | Evidence / next verification |
| --- | --- | --- | --- | --- | --- | --- |
| Practice model | Practice tenant profile | Planned / configuration-dependent | Included target | Included target | Included target | Onboarding/pricing doc says separate practice profile is needed; not production-ready. |
| Client books | Multiple client/company accounting entities | Planned / configuration-dependent | Up to 5 target | Up to 25 target | Up to 50 target | Gap matrix says CA/bookkeeper model is not yet modeled. Must not rely on tenant_id alone. |
| Client access | Company/client switcher | Planned / configuration-dependent | Included target | Included target | Included target | Needs accounting entity/client model and app access rules. |
| Client access | Client assignment and staff access control | Planned / configuration-dependent | Limited target | Included target | Included target | Phase 2C target; not current production promise. |
| Practice users | Staff users | Planned / configuration-dependent | 1 | 5 | 15 | User/role backend contracts are Phase 2B/2C. |
| Practice workflow | Client document queue | Planned / configuration-dependent | Not included | Included target | Included target | Phase 2C/2D; do not promise until document workflow exists. |
| Practice workflow | Work assignment | Planned / configuration-dependent | Not included | Included target | Included target | Phase 2C target. |
| Compliance | Compliance tracking | Planned / configuration-dependent | Manual target | Included target | Included target | Phase 2C target for GST/TDS/income tax/audit due dates. |
| OCR / AI | OCR documents | Planned / configuration-dependent | 0/month | 500/month target | Fair-use unlimited target | Pricing docs include limits, but implementation needs verification before public claims. |
| OCR / AI | AI MIS / reconciliation assistance | Planned / configuration-dependent | Not included | Planned | Planned | Deterministic reports must come first. Human review required. |
| Support | Priority support and onboarding review | Planned / configuration-dependent | Not included | Included where sold | Included | Define service levels before publishing. |

## Minimum Publishable Regular Business Packages

### Free

Do not publish Free as usable unless these are verified:

- One company and one user entitlement.
- Party master.
- Manual vouchers.
- Basic sales and purchase documents.
- Ledger, trial balance, balance sheet, receipts/payments, and profit/loss reports.
- No OCR, no AI, no CA dashboard.
- Posted entries remain immutable and reversible only through controlled workflows.

### Basic

Do not publish Basic unless Free plus these are verified:

- GST preparation reports clearly labeled as preparation, not filing.
- TDS/TCS tracking.
- Basic document upload/OCR queue only if implemented and verified; otherwise remove the 25/month OCR claim from public copy.
- Email/support terms are defined.

### Starter

Do not publish Starter unless Basic plus these are verified:

- Multi-company entitlement or company switch model.
- Bank reconciliation.
- Receivable/payable ageing.
- Customer/vendor statements.
- Inventory basics.
- Opening balance flow for new customers.
- AI categorization claims remain "suggestion only" and require human review.

### Growth

Do not publish Growth unless Starter plus these are verified:

- Higher company/document limits enforced by entitlement.
- AI MIS or reconciliation assistance, if advertised, is source-backed and non-posting.
- Advanced reports are reproducible from posted records.
- Priority support and onboarding review terms are defined.

## Minimum Publishable CA / Bookkeeper Packages

CA/bookkeeper packages should remain "Get Final Quote" or "Early Access" until these are implemented and verified:

- Practice tenant profile.
- Client/company accounting entity model.
- Client switcher.
- Staff-user access by assigned client.
- Client document queue.
- Compliance tracking.
- Work assignment.
- Audit trail for client/staff actions.
- No cross-client data leakage.

The current pricing numbers can be used for planning, but public payment pages should wait until Phase 2C client/access controls are real.

## Pricing Justification

The regular-business pricing is defensible if the published feature copy stays conservative:

- INR 499/month Basic is justified when GST/TDS prep, core reports, parties, invoices, vouchers, and one-company books are verified.
- INR 999/month Starter is justified when bank reconciliation, ageing, statements, inventory basics, and multi-company support are verified.
- INR 1,499/month Growth is justified only if higher document limits, advanced reports, support, and AI/OCR assistance are genuinely available and clearly non-posting.

The CA/bookkeeper pricing is attractive, but higher risk:

- The value is strong if multi-client access and document queues work.
- The current risk is cross-client confidentiality and access control.
- Do not sell it as production-ready until tenant + client/entity + role + permission checks are tested.

## Current Decision Notes

- Show transparent Regular Business pricing if the public page clearly labels planned OCR/AI/practice features.
- Use `Get Final Quote` for CA/bookkeeper practices until Phase 2C is verified.
- Keep implementation/migration/training as a separate quote.
- Keep live GST filing, bank API sync, payment execution, OCR auto-posting, and AI posting out of public claims.
- AI/OCR may create suggestions or drafts only; a permitted user must approve any ledger posting.

## Next Verification Steps

1. Run focused backend tests for `/api/v1/business` parties, vouchers, invoices, bills, notes, GST/TDS, inventory, bank reconciliation, and reports.
2. Extend the MitraBooks Playwright smoke from route availability into safe validation for reports, settings, GST/TDS, bank reconciliation, and export/print paths.
3. Run a safe business-demo tenant E2E: create party -> post voucher -> create invoice -> create bill -> create credit/debit note -> verify ledger/trial balance/balance sheet -> reverse one posted record.
4. Add a separate CA-practice design/E2E plan before creating payment pages for CA packages.
5. Update this checklist from `Partially working` to `Working` only after test evidence exists.
