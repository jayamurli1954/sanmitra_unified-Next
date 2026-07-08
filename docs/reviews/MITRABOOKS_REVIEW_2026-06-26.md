# MitraBooks Review Report

Date: 2026-06-26
Workspace: `D:\sanmitra_unified-Next`
Scope: MitraBooks planned-module review, security/vulnerability review, current-vs-target gap matrix, and verification snapshot

> **Living trackers (post-2026-06-26):** Module completion, E2E gates, and security remediation status are maintained in [`docs/operations/MITRABOOKS_PENDING_GAP_TODO.md`](../operations/MITRABOOKS_PENDING_GAP_TODO.md) (see **Security P0/P1/P2**). PR-scoped security fix order is in [`docs/reviews/SECURITY_REMEDIATION_PR_PLAN.md`](SECURITY_REMEDIATION_PR_PLAN.md). Full static review snapshot: [`docs/operations/Code_Review-Sanmitra_Unified-Next.docx`](../operations/Code_Review-Sanmitra_Unified-Next.docx).

## Executive Summary

MitraBooks is materially further along than some of the master planning language suggests. Core ERP slices are implemented in code for parties, vouchers, invoices, bills, credit/debit notes, GST prep/reports, TDS/TCS, bank reconciliation, inventory basics, fixed assets, dimensions, opening balances, year-end flows, HR, and manufacturing/cost-centre add-ons.

The correct conclusion is not "all planned modules are fully complete." The more accurate conclusion is:

- Core MitraBooks ERP is largely implemented.
- HR and manufacturing/cost-centre add-ons are implemented at route/service level.
- Several master-reference documents still describe parts of the system as planned or partial even where code and tests now exist.
- Production-readiness gaps remain around compliance signoff, browser E2E depth, approvals, attachment/document depth, multi-location inventory, data-health/data-portability, and cross-database consistency hardening.

## Security Findings

| Severity | Finding | Evidence | Why it matters |
| --- | --- | --- | --- |
| High | Cross-database consistency is not atomic for some posted financial workflows | [app/accounting/service.py](/abs/path/D:/sanmitra_unified-Next/app/accounting/service.py:670) commits inside `post_journal_entry`; callers then write Mongo after the PostgreSQL commit, e.g. [app/modules/hr/payroll_run.py](/abs/path/D:/sanmitra_unified-Next/app/modules/hr/payroll_run.py:262) and [app/modules/business/bulk_import.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/bulk_import.py:428) | If the Mongo write fails after the accounting commit, the ledger is permanently posted without its source-domain record. That violates the repo guardrail on cross-store completion boundaries. |
| Medium | CA invite flow exposes temporary passwords back to the API caller and frontend UI | Password is injected into the response in [app/modules/business/ca_access.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/ca_access.py:149) and [app/modules/business/ca_access.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/ca_access.py:176), returned by [app/modules/business/router.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/router.py:2997), and rendered by [frontend/mitrabooks-erp/app.js](/abs/path/D:/sanmitra_unified-Next/frontend/mitrabooks-erp/app.js:17310) | Admins do not need the plaintext password echoed back once email delivery is attempted. This increases credential exposure in browser state, logs, screenshots, and support flows. **Update (2026-07-08):** `ca_access.py` now uses token-based invite acceptance; treat plaintext-password echo as closed if verified in tests/UI. Remaining gap: preview/accept rate limits and response minimization (`SEC-P1-11` in pending gap tracker). |
| Medium | Invalid `X-App-Key` values fail open to the default app instead of being rejected | [app/core/tenants/context.py](/abs/path/D:/sanmitra_unified-Next/app/core/tenants/context.py:30) returns the default app when the supplied key is not allowed; middleware then accepts that normalized value at [app/core/tenants/context.py](/abs/path/D:/sanmitra_unified-Next/app/core/tenants/context.py:89) | Your workspace policy says invalid `X-App-Key` must fail gracefully. Current behavior silently coerces malformed app keys to the default app context, which weakens product-boundary enforcement on default-app surfaces. |

## Completion Matrix

| Area | Review status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Parties and typed vouchers | Implemented | `/business/parties`, `/business` voucher routes and accounting service paths exist; route smoke tests exist | More browser E2E depth desirable |
| Sales invoices | Implemented | [app/modules/business/router.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/router.py:1169), service posting, PDF route, cancellation route | Approval workflow, richer templates, compliance signoff, deeper E2E |
| Purchase bills | Implemented | [app/modules/business/router.py](/abs/path/D:/sanmitra_unified-Next/app/modules/business/router.py:1378), payment/ITC routes exist | Approval workflow, attachments/document support, compliance signoff |
| Credit/debit notes | Implemented | Cancellation routes and posting service paths exist | Stronger source-document linkage and E2E depth |
| GST prep/reports | Implemented | GSTR-1, GSTR-3B, GSTR-4, GSTR-2B reconcile, GST settlement routes exist | Filing semantics/compliance signoff; live filing remains deferred |
| TDS/TCS | Implemented | TDS routes and tests exist | Compliance signoff and workflow depth |
| Bank reconciliation | Implemented | Statement import/match/reverse routes exist | Safer E2E around import/match/reverse |
| Inventory basics | Implemented | Item master, stock register, closing-stock posting routes exist | Multi-location, batch/serial, stock issue/adjustment depth |
| Fixed assets and depreciation | Implemented | Fixed-asset and depreciation routes exist | More end-to-end verification |
| Dimensions | Implemented | Create/list/report/deactivate routes exist | Expand tagging coverage and E2E |
| Opening balances and year-end | Implemented | Opening-balance preview/import/export routes and year-end related service flows exist | More staged E2E and rollback-path verification |
| CA access | Implemented | Invite/preview/accept/revoke flows exist | Remove plaintext password exposure; add safer credential handling |
| HR add-on | Implemented | Employee, payroll, leave, tax, FNF, analytics routes exist in [app/modules/hr/router.py](/abs/path/D:/sanmitra_unified-Next/app/modules/hr/router.py:109) | Production hardening and more integration/E2E |
| Manufacturing and cost-centre add-on | Implemented | BOM, work order, cost-centre budget/report routes exist in [app/modules/manufacturing/router.py](/abs/path/D:/sanmitra_unified-Next/app/modules/manufacturing/router.py:54) | Dedicated test coverage appears thin or absent in current test tree |

## Planned vs Gap Matrix

| Planned/target item | Current state observed | Gap |
| --- | --- | --- |
| Approval workflows | Mentioned repeatedly in master docs as target | Still mostly not present across invoices, bills, refunds, inventory, and payables |
| Compliance signoff | Docs correctly still treat GST/TDS and filing-adjacent features as not production-certified | Needs reviewed business/compliance validation before stronger product claims |
| Browser E2E depth | Some smoke/verification artifacts exist | Core routes render, but docs still correctly call for deeper staged E2E over posting, exports, print/PDF, reconciliation, and settings |
| Attachments/document support | Still called out in purchase lifecycle gap notes | Not yet at the same depth as core posting flows |
| Batch/serial/multi-location inventory | Still marked deferred in master docs | No evidence of full implementation in current active backend |
| Data Health Score | Still legacy-planned | No implemented active module located in this review |
| Data portability/export governance | Some export/report slices exist | Tenant-safe export permissions/audit/scope are still not fully closed |
| Live GST/e-way bill/bank execution/OCR auto-posting | Docs correctly keep this out of present-scope claims | Remains deferred and should stay deferred |
| Cross-store compensation boundary | Not fully closed | High-priority engineering gap because financial posting and Mongo source records are not always treated as one completion unit |
| Documentation alignment | Code is ahead of several master narratives | Master docs need an explicit current-state refresh so completion reporting stops understating implemented modules while still preserving non-production gaps |

## Verification Snapshot

- Focused pytest slice passed:
  - `tests/test_hr_payroll_run.py`
  - `tests/test_bank_recon.py`
  - `tests/test_inventory.py`
  - `tests/test_fixed_assets.py`
  - `tests/test_dimensions.py`
  - `tests/test_gstr1_return.py`
  - `tests/test_gstr3b_return.py`
  - `tests/test_accounting_validation.py`
- Result: `64 passed`
- Warnings observed: Pydantic v1-style validator/Field deprecation warnings and `python_multipart` pending deprecation

## Recommendations

1. Fix the three security issues above before calling the ERP core security-reviewed.
2. Refresh the master MitraBooks docs so "current state" matches the implemented backend and test reality.
3. Keep production claims conservative until the staged browser E2E and compliance signoff gaps are closed.
4. Add dedicated manufacturing tests and explicit cross-database failure tests for payroll, bulk import, invoice/bill posting, and similar Mongo-plus-ledger flows.
