# GruhaMitra Feature Verification Checklist

Date: 2026-06-13

Purpose: map GruhaMitra features against current verification status and the Starter, Growth, and Professional pricing tiers before publishing final pricing or payment pages.

This checklist is a product, sales, and E2E planning aid. It does not replace tenant isolation, app-key isolation, RBAC, accounting, or smoke/E2E tests.

## Status Legend

| Status | Meaning |
| --- | --- |
| Working | Smoke checklist or current docs indicate the feature is usable and has been verified at least at basic workflow level. |
| Partially working | UI/settings or partial workflow exists, but the full business cycle still needs E2E verification. |
| Available / needs verification | Existing docs claim the feature, but this checklist has not independently verified it in the current turn. |
| Planned / configuration-dependent | Feature depends on tenant setup, provider configuration, custom implementation, or later roadmap scope. |
| Not included | Should not be promised in that plan. |

## Pricing Tier Rule

Recommended packaging based on the current internal pricing playbook:

| Tier | Commercial role | Packaging rule |
| --- | --- | --- |
| Starter | Entry plan for small societies | Core society records, basic admin/resident access, maintenance billing basics, complaints, notices, and standard support. |
| Growth | Recommended plan for active societies | Starter plus accounting-led operations, member dues, reports, stronger billing controls, meetings/governance, and priority support. |
| Professional | Larger or governance-heavy societies | Growth plus advanced controls, integrations, custom onboarding, exports, migration support, and higher-touch support. |

## Verification Matrix

| Feature area | Feature | Current status | Starter | Growth | Professional | Evidence / next verification |
| --- | --- | --- | --- | --- | --- | --- |
| Society setup | Society profile save and reload | Working | Included | Included | Included | Stage 4 smoke checklist marks Society Profile as PASS. |
| Society setup | Blocks/towers/flats setup | Working | Included | Included | Included | Stage 4 smoke checklist marks Flats/Blocks as PASS. |
| Society setup | Member configuration settings | Working | Included | Included | Included | Stage 4 smoke checklist marks Member Config as PASS. |
| Society setup | Billing rules settings | Working | Included | Included | Included | Stage 4 smoke checklist marks Billing Rules as PASS. Full bill-generation E2E still separate. |
| Society setup | Late fees and penalties settings | Working | Included | Included | Included | Stage 4 smoke checklist marks Late Fees/Penalties as PASS. |
| Society setup | Accounting settings | Working | Not included | Included | Included | Stage 4 smoke checklist says core settings save flows are working. Verify report/posting links in Growth. |
| Members/residents | Owner/tenant member onboarding | Working | Included | Included | Included | Stage 4 smoke checklist marks Member Onboarding as PASS. |
| Members/residents | Resident join request flow | Available / needs verification | Included | Included | Included | Technical info and user guide document resident registration. Verify with demo resident/admin flow. |
| Members/residents | Owner/tenant classification and flat association | Available / needs verification | Included | Included | Included | Technical info documents this. Verify create/edit/read behavior by role. |
| Members/residents | Resident/member visibility controls | Working | Included | Included | Included | Member Config PASS; verify resident cannot cross-view other units. |
| Maintenance billing | Monthly bill generation | Partially working | Included | Included | Included | Stage 4 checklist marks Generate Bills as TODO. Must verify generate -> view -> no runtime errors. |
| Maintenance billing | Configurable charges / per-flat funds | Available / needs verification | Included | Included | Included | Technical info documents fixed expenses, per-person water, and fund-based rules. Verify bill calculation samples. |
| Maintenance billing | Late fee/penalty application | Partially working | Included | Included | Included | Settings PASS; verify generated bill applies penalty correctly. |
| Maintenance billing | Bill breakdown and existing bill view | Available / needs verification | Included | Included | Included | Technical info documents bill view/breakdown. Verify through admin UI. |
| Maintenance billing | Bill reversal/adjustment | Planned / configuration-dependent | Not included | Included where enabled | Included | Stage 4 checklist includes reversal/adjustment as TODO where enabled. Do not promise until verified. |
| Collections/receipts | Maintenance receipt posting | Partially working | Not included | Included | Included | User guide documents receipt posting; Stage 4 Collections/Receipts is TODO. Verify receipt -> dues reduction. |
| Collections/receipts | Dues tracking after receipt | Partially working | Basic view | Included | Included | Stage 4 Collections/Receipts is TODO. Verify pending dues before/after receipt. |
| Collections/receipts | Receipt print/PDF | Available / needs verification | Not included | Included where enabled | Included | Technical info says voucher PDFs/prints where enabled. Verify generated output before publishing. |
| Accounting | Chart of accounts | Available / needs verification | Not included | Included | Included | User guide documents accounting setup. Verify tenant-scoped chart setup. |
| Accounting | Ledger | Available / needs verification | Not included | Included | Included | Technical info claims ledger. Verify report opens and matches posted entries. |
| Accounting | Trial balance | Available / needs verification | Not included | Included | Included | Technical info claims trial balance. Verify balanced report after test postings. |
| Accounting | Receipts and payments report | Available / needs verification | Not included | Included | Included | Technical info claims report. Verify with posted receipt/payment sample. |
| Accounting | Income and expenditure report | Available / needs verification | Not included | Included | Included | Technical info claims report. Verify with generated bills and expenses. |
| Accounting | Balance sheet | Available / needs verification | Not included | Included | Included | Technical info claims report. Verify after opening balances/postings. |
| Accounting | Member dues report | Available / needs verification | Basic view | Included | Included | User guide documents member dues report. Verify tenant and member scope. |
| Accounting | All financial postings routed through MitraBooks | Partially working | Not included | Required | Required | Stage 4 Post Bills to Accounting and Accounting Evidence are TODO. This is mandatory before calling Growth/Professional fully verified. |
| Portal/access | Public GruhaMitra landing page | Working | Included | Included | Included | Playwright smoke `frontend/e2e/gruhamitra-smoke.spec.js` verifies built PWA landing page, manifest, pricing cards, core feature cards, and entry links. |
| Portal/access | Login, society onboarding, and resident signup routes | Working | Included | Included | Included | Playwright smoke verifies these public routes render through in-app navigation from `/gruhamitra/`. |
| Portal/access | Admin login and dashboard | Working | Included | Included | Included | Stage 4 Auth + Module Context and Dashboard are PASS; Playwright smoke also verifies dashboard shell with mocked backend data. |
| Portal/access | Resident/member login | Available / needs verification | Included | Included | Included | User guide documents demo resident login. Verify resident dashboard and access limits. |
| Portal/access | Resident dues visibility | Available / needs verification | Included | Included | Included | User guide says dues visible where enabled. Verify by resident role. |
| Portal/access | Resident notices/meetings visibility | Available / needs verification | Included | Included | Included | User guide documents eligible member visibility. Verify by resident role. |
| Portal/access | Basic profile/flat visibility | Available / needs verification | Included | Included | Included | Verify resident can see only own profile/unit context. |
| Complaints/helpdesk | Admin complaint create/update lifecycle | Working | Included | Included | Included | Stage 4 Complaints row is PASS. |
| Complaints/helpdesk | Resident complaint creation | Available / needs verification | Included | Included | Included | User guide documents resident complaint creation. Verify resident flow and tenant scope. |
| Complaints/helpdesk | Complaint history/status tracking | Working | Included | Included | Included | Stage 4 marks complaint lifecycle as PASS; verify resident-facing history separately. |
| Notices/communication | Messages / notice-room communication | Working | Included | Included | Included | Stage 4 Messages row is PASS. |
| Notices/communication | Notices/announcements | Available / needs verification | Included | Included | Included | Technical info and user guide document notices. Verify create -> resident visibility. |
| Meetings/governance | Meeting creation/list/view | Working | Not included | Included | Included | Stage 4 Meetings row is PASS. |
| Meetings/governance | Attendance, minutes, resolutions | Available / needs verification | Not included | Included | Included | Technical info claims these. Verify create/edit/print flow. |
| Meetings/governance | Meeting notices visible to eligible members | Available / needs verification | Not included | Included | Included | User guide documents expected behavior. Verify resident/member view. |
| Reports/exports | Society summary report | Available / needs verification | Included | Included | Included | Technical info claims society summary. Verify report opens and uses society details. |
| Reports/exports | Accounting reports for committee/auditor | Available / needs verification | Not included | Included | Included | Verify ledger, trial balance, member dues, balance sheet with test data. |
| Reports/exports | Excel/PDF/print support | Available / needs verification | Not included | Included where enabled | Included | Technical info says where enabled. Verify each export before promising. |
| Integrations | Payment gateway setup | Planned / configuration-dependent | Not included | Optional add-on | Optional add-on | Technical info marks payment gateway as configuration-dependent. Quote separately. |
| Integrations | SMS/WhatsApp/email automation | Planned / configuration-dependent | Not included | Optional add-on | Optional add-on | Technical info marks notifications as configuration-dependent. Quote separately. |
| Integrations | Custom invoice/receipt formats | Planned / configuration-dependent | Not included | Optional add-on | Optional/custom | Quote based on scope. |
| Integrations | API/webhooks | Planned / configuration-dependent | Not included | Not included | Optional/custom | Internal pricing playbook reserves integrations for Professional. |
| Advanced operations | Facility/amenity booking | Planned / configuration-dependent | Not included | Optional add-on | Optional/custom | Competitor feature, but not verified as current GruhaMitra feature in docs reviewed. |
| Advanced operations | Parking manager | Planned / configuration-dependent | Not included | Optional add-on | Optional/custom | Competitor feature; GruhaMitra skill mentions parking allocation, but current docs reviewed do not prove UI readiness. |
| Advanced operations | Vendor payments | Planned / configuration-dependent | Not included | Optional add-on | Included where enabled | Must post through MitraBooks accounting before being promised. |
| Advanced operations | Staff/workforce management | Planned / configuration-dependent | Not included | Not included | Optional/custom | Competitor feature; keep out of standard pricing until implemented and verified. |
| Advanced operations | Gate/security hardware or guard app | Planned / configuration-dependent | Not included | Not included | Optional/custom | Do not claim MyGate/NoBrokerHood parity unless separately implemented. |
| Onboarding | Tenant setup and initial configuration | Available / needs verification | Paid setup | Paid setup | Included/custom by quote | Technical info documents onboarding sequence. Keep as setup/migration line item. |
| Onboarding | Excel/manual data migration | Planned / configuration-dependent | Paid add-on | Paid add-on | Included/custom by quote | Quote separately based on data quality and volume. |
| Support | Standard support | Available / needs verification | Included | Included | Included | Define response windows before publishing. |
| Support | Priority support | Planned / configuration-dependent | Not included | Included | Included+ | Internal pricing playbook assigns priority support to Growth/Professional. |

## Playwright E2E Status

Latest local run:

```text
npm run build
npx.cmd playwright test e2e/gruhamitra-smoke.spec.js --project=chromium
```

Result:

```text
4 passed
```

Verified:

- Built GruhaMitra PWA artifact exists under `/gruhamitra/`.
- `/gruhamitra/manifest.json` is reachable.
- Public landing page renders core product positioning, features, plans, and entry links.
- Login, society onboarding, and resident signup routes render through in-app navigation.
- Authenticated dashboard shell renders with demo local-storage session and mocked backend responses.
- Core authenticated route screens load without route-level crashes for maintenance, accounting, members, complaints, reports, message, meeting, and settings.

Important limitation:

- This Playwright smoke uses mocked backend responses for authenticated routes. It verifies frontend/PWA shell health and route availability, not live backend correctness.
- It does not yet prove maintenance bill generation, bill posting, receipt posting, dues reduction, ledger/trial balance correctness, tenant isolation, or debit-credit accounting invariants against a real GruhaMitra demo tenant.
- Direct local deep links such as `/gruhamitra/login` did not work through `frontend/scripts/serve_build.py` because the static server falls back to root `index.html` instead of `gruhamitra/index.html`. The deployed Vercel routing should be checked separately.

## Minimum Publishable Starter Package

Starter should not be published unless these are verified in a demo tenant:

- Society profile.
- Blocks/flats.
- Members/residents.
- Admin login and dashboard.
- Resident/member login.
- Billing rules and basic bill generation.
- Basic dues visibility.
- Complaints.
- Notices/messages.
- Standard support terms.

## Minimum Publishable Growth Package

Growth should not be published as the recommended plan unless these are verified:

- All Starter items.
- Maintenance receipt posting.
- Dues reduction after receipt.
- Ledger.
- Trial balance.
- Receipts and payments.
- Income and expenditure.
- Balance sheet.
- Member dues report.
- Meeting notices, minutes, and resolutions.
- Financial postings routed through MitraBooks with balanced debit/credit evidence.

## Minimum Publishable Professional Package

Professional should be quote-led until these are scoped per customer:

- All Growth items.
- Advanced roles/approval controls.
- Excel/manual data migration.
- Custom report/export requirements.
- Payment gateway and notification setup, if required.
- API/webhooks or external integrations, if required.
- Any gate/security, staff, facility, vendor, or parking enhancements beyond the verified core.

## Current Pricing Decision Note

Before publishing GruhaMitra payment pages, standardize the pricing model across docs:

- `docs/operations/PRICING_PLAYBOOK_INTERNAL.md` currently uses fixed-plus-per-flat pricing.
- `docs/operations/GRUHAMITRA_CLIENT_TECHNICAL_INFORMATION.md` currently uses per-flat-only pricing.

Recommendation: keep public pricing transparent, but use `Get Final Quote` for setup, migration, payment gateway, notification, and custom Professional scope.

## Next Verification Steps

1. Create or use a clean GruhaMitra demo tenant.
2. Run the Starter checklist as admin and resident.
3. Run the Growth billing cycle: generate bill -> post to accounting -> verify ledger/trial balance -> post receipt -> verify dues reduction.
4. Capture screenshots and API failures in `docs/operations/E2E_VERIFICATION_REPORT.md`.
5. Update this checklist from `Available / needs verification` to `Working` only after evidence exists.
