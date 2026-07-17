# GruhaMitra Stage 4 Smoke Checklist

Date: 2026-05-25 (updated 2026-07-17)  
Scope: GruhaMitra workflows inside MitraBooks Unified ERP shell  
Environment: Production URLs (`gruhamitra.sanmitratech.in` / `www.gruhamitra.sanmitratech.in`)

## Current State

- **Stage 4 started 2026-07-17** after MandirMitra Stage 3 machine signoff PASS (`backend-v1.3.0`).
- Hosted Track 0 auth PASS for demo tenant `gruhamitra-demo-society` (`HOUSING`, modules `housing`/`accounting`/`audit`). See `TRACK0_GRUHA_STAGING_CREDENTIALS_RUNBOOK.md`.
- GruhaMitra login and dashboard load through the deployed frontend.
- Core settings save flows are working:
  - Society Profile
  - Flats and Blocks
  - Member Config
  - Billing Rules
  - Late Fees and Penalties
  - Accounting Settings
- Meetings, Messages, and Complaints screens are loading and usable.
- Member onboarding POST path mismatch (`/member-onboarding` vs `/member-onboarding/`) was fixed in backend (`main` commit `cc6d3d9`).

## Target State (Stage 4 Gate)

GruhaMitra should be usable in production for housing operations while preserving tenant/app isolation and MitraBooks accounting guardrails.

## Gap (Pending Verification)

- Maintenance billing full cycle (generate -> post -> verify) not fully confirmed.
- Accounting posting verification for generated bills not fully confirmed.
- Collection/receipt flows against generated bills not fully confirmed.
- Notification and payment gateway are not configured by design (admin-dependent).

## Deferred Scope (Not Part of This Checklist)

- LegalMitra flows and any out-of-scope InvestMitra workstream.
- Broad MitraBooks business ERP workflows outside GruhaMitra needs.
- Payment gateway onboarding and provider-specific notification setup.

## Preconditions

1. User can login with valid GruhaMitra tenant credentials.
2. Tenant is `organization_type=HOUSING` with relevant modules enabled.
3. `X-App-Key: gruhamitra` context is active.
4. At least one flat/unit exists.

## Smoke Checklist

| Area | Step | Expected Result | Status |
| --- | --- | --- | --- |
| Auth + Module Context | Login from `https://www.gruhamitra.sanmitratech.in` | Lands in GruhaMitra app; no redirect loop to MandirMitra | PASS (Track 0 hosted auth 2026-07-17: `gruhamitra-demo-society` / HOUSING / housing+accounting+audit) |
| Dashboard | Open dashboard widgets/cards | Tenant-scoped counts and cards render | PASS |
| Society Profile | Edit + save profile fields | Changes persist after refresh | PASS |
| Flats/Blocks | Create/edit block and flat | Records save and reload correctly | PASS |
| Member Onboarding | Add owner/tenant member via form | Member created without 405/500 errors | PASS |
| Member Config | Update visibility/config settings | Save success and persisted state | PASS |
| Billing Rules | Configure billing rules | Save success and values retained | PASS |
| Late Fees/Penalties | Configure rates/rules | Save success and values retained | PASS |
| Meetings | Create/list a meeting | Record appears and can be viewed | PASS |
| Messages | Send message in room/thread | Message appears with correct tenant scope | PASS |
| Complaints | Create/update complaint | Complaint lifecycle works in same tenant | PASS |
| Local PWA shell smoke | `npx playwright test e2e/gruhamitra-smoke.spec.js` against built PWA | Landing, login/onboarding, mocked dashboard + core routes | PASS (2026-07-17, 4/4) |
| Generate Bills | Run bill generation for a month | Bills generated; no validation/runtime errors | TODO |
| Post Bills to Accounting | Post generated bills | Posting succeeds via shared accounting service | TODO |
| Accounting Evidence | Verify journal/ledger impact | Debit=Credit; tenant-scoped entries; no direct balance mutation | TODO |
| Collections/Receipts | Record collection for bill | Receipt/collection updates pending dues correctly | TODO |
| Reversal/Adjustment | Reverse one test bill/payment (if enabled) | Reversal entry created; original posted entry immutable | TODO |

## Accounting Guardrail Checks (Mandatory)

1. Generated/post flows must create balanced journal entries (`sum(debits) == sum(credits)`).
2. No direct account balance edits.
3. Posted entries remain immutable; corrections happen by reversal/adjustment.
4. Entries are tenant-scoped and traceable to GruhaMitra source action.

## Evidence to Capture

- Screenshots for:
  - Bill generation result
  - Bill posting confirmation
  - Accounting report/drill-down showing balanced entries
  - Collection/receipt confirmation
- Browser Network/Console capture for any non-2xx API call.
- Endpoint + payload + response code for each failure.

## Exit Criteria for Stage 4

Stage 4 can be marked ready when:

1. All PASS/TODO rows above are PASS, except explicitly deferred rows.
2. Billing-to-accounting path is verified with evidence.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains.
4. Result is recorded in `docs/operations/E2E_VERIFICATION_REPORT.md` under GruhaMitra section.
