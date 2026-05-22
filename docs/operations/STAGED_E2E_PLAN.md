# Staged E2E Plan

## Purpose

SanMitra E2E validation must be practical for a one-person platform owner. Do not attempt full-platform E2E across all products in one pass unless each stage below is already green.

The goal is to isolate failures, reduce troubleshooting load, and build confidence stage by stage.

## Current State

- LegalMitra is already tested and deployed live.
- MitraBooks ERP is the planned unified shell for MitraBooks, MandirMitra, and GruhaMitra workflows.
- Current execution priority is MandirMitra live-readiness first, after only the minimum MitraBooks ERP/accounting foundation required to host it safely.
- GruhaMitra starts after the MandirMitra live-ready gate passes, because both MandirMitra and GruhaMitra already have live legacy frontends and should be migrated one at a time.
- InvestMitra remains a separate product experience.
- Full combined E2E across every product would create too much support and debugging surface for one maintainer.

## Target State

Each product area has a focused E2E checklist and a clear pass/fail gate. A later stage should not expand scope until the previous stage has passed its smoke and E2E checks.

## Active Workflow Recap

The current live-readiness workflow is:

1. LegalMitra remains the stable live baseline.
2. MitraBooks is used as the accounting engine and ERP shell foundation, not as the full business ERP delivery focus yet.
3. MandirMitra is completed and made live-ready first inside that foundation.
4. GruhaMitra starts only after MandirMitra passes the live-ready gate.
5. Full MitraBooks business ERP expansion starts after MandirMitra and GruhaMitra are completed and deployed live.

Any Stage 2 work must be judged by whether it supports MandirMitra/GruhaMitra live readiness. Broad business ERP features are tracked in the PRD and gap matrix, but they are not the active delivery track yet.

## E2E Stage Order

### Stage 1: LegalMitra Baseline

Goal: confirm the live LegalMitra product still works after unified-platform backend changes.

Validate:

- Login and authenticated legal routes.
- Tenant/app-key isolation.
- Case, document, compliance, and RAG workflows where currently implemented.
- Source attribution for legal research.
- No regression in the deployed LegalMitra experience.

Gate: LegalMitra smoke and critical legal workflows pass.

### Stage 2: MitraBooks ERP Core

Goal: prove the shared ERP/accounting foundation needed by MandirMitra is stable before expanding merged domain workflows.

Validate:

- Login and tenant context.
- `X-App-Key` handling.
- Module registry and enabled module rendering.
- Platform owner dashboard can show module-wise onboarding requests, pending approvals, subscription status, enabled modules, and tenant KPIs needed to operate MandirMitra tenants.
- Chart of Accounts.
- Journal posting.
- Ledger, trial balance, and financial reports.
- RBAC allow/deny checks.
- Idempotency for financial postings.
- Accounting invariant: debits equal credits.

Gate: MitraBooks ERP core can be trusted as the MandirMitra accounting, tenant-context, module-access, reporting, and navigation foundation.

Scope reference: MitraBooks ERP business workflow phases are tracked in `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md`.

Deferred during this gate:

- Broad MitraBooks business parties, sales, purchases, GST, inventory, MIS, exports, and CA/bookkeeper workflow work unless directly required for MandirMitra accounting or shell stability.

### Stage 3: MandirMitra in MitraBooks ERP

Goal: complete MandirMitra to live-ready parity inside the unified ERP shell before starting GruhaMitra migration.

Validate:

- Module-wise temple/trust onboarding requires `X-App-Key` and creates a `TEMPLE` tenant with the `temple`, `accounting`, and `audit` modules enabled.
- Tenant login lands in the MandirMitra workspace without module access leakage or app-key confusion.
- MandirMitra navigation works for overview, donations, sevas, public payments, exceptions, receipts, and accounting/report panels where implemented.
- Public devotee payment works without login.
- Public devotee flow allows temple/trust selection, donation or seva selection, amount/details entry, and payment through the selected temple/trust's configured UPI QR/payment instructions.
- Parlathya Prathishtana remains a known reference tenant/example for validating public payment behavior.
- Devotee management.
- Donation creation.
- Donation receipt generation is mandatory and stable.
- Donation receipt PDF title is `ದೇಣಿಗೆ ರಶೀದಿ / Donation Receipt`.
- Donation receipt uses `ದೇಣಿಗೆ` terminology and does not include seva-only note/signature text.
- Seva booking.
- Seva receipt PDF title is `ಸೇವಾ ರಶೀದಿ / Seva Receipt`.
- Seva receipt uses the `ಭಕ್ತ / Devotee` label.
- Seva receipt includes the Kannada received-with-thanks sentence: `ಈ ಕೆಳಗೆ ಕಾಣಿಸಿದ ಸೇವೆಯ ಸಲುವಾಗಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ`.
- Hundi/festival flows where implemented.
- Donation and seva posting through MitraBooks accounting.
- Expense posting works through the shared accounting engine where MandirMitra requires expense recording.
- Trial Balance balances after donation, seva, and expense postings.
- Trial Balance rows drill down to vouchers.
- Income and Expenditure, Receipts and Payments, and Balance Sheet match the posted vouchers.
- Receipt/payment exception review supports verify, reject, correction, and audit trace where implemented.
- Receipt numbering is stable, tenant-scoped, and auditable.
- Tenant-scoped temple data.
- `mandirmitra` app context cannot read or mutate GruhaMitra or MitraBooks business data.
- GruhaMitra and MitraBooks app contexts cannot read or mutate MandirMitra temple data.
- No MandirMitra financial workflow writes directly to ledger tables or mutates balances outside the accounting service.
- Repeatable smoke/E2E evidence is recorded before calling the stage live-ready.

Gate: MandirMitra workflows work through the shared ERP shell with tenant isolation, app-key isolation, correct bilingual receipts, accounting correctness, auditability, and a repeatable smoke/E2E checklist. Only after this gate passes should GruhaMitra migration start.

Latest evidence:

- 2026-05-21 local smoke verified donation receipt PDF, seva receipt PDF, expense receipt, donation/seva/expense postings, trial balance, voucher drill-down, Income and Expenditure, Receipts and Payments, and Balance Sheet.
- 2026-05-21 commit `73ebf0b` fixed seed tenant context so `seed-tenant-1` remains `TEMPLE` with `temple`, `accounting`, and `audit` enabled for `mandirmitra`.
- 2026-05-21 `python scripts\mandirmitra_stage3_smoke.py` passed compile checks and 119 focused tests; manual/live checklist exists at `docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md`.
- 2026-05-21 backend/API live smoke passed for public temple selection, public UPI config/intent, no-login public donation submission, staff verification, correction, rejection, audit trace, receipt PDF text, accounting reports, shared drill-down, and voucher detail.
- 2026-05-21 `python scripts\mandirmitra_stage3_browser_smoke.py` passed against the local backend/frontend and saved a screenshot at `tmp\mandir-stage3-browser-smoke.png`.
- 2026-05-22 Panchang was wired into the MandirMitra ERP shell as a rendered workspace backed by `/api/v1/panchang/today`; browser smoke now verifies Today Panchang and Tithi text, not only the navigation label.
- 2026-05-22 deployment-readiness review was captured at `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md`.
- 2026-05-22 Reports was split from Receipts in the MandirMitra ERP shell and now renders donation category, detailed donation, detailed seva, seva schedule, and recent devotee data.
- 2026-05-22 first live-cut decisions were captured at `docs/operations/MANDIRMITRA_FIRST_LIVE_CUT_DECISIONS.md`: donation, seva, public payment, receipt, Panchang, reports, and accounting are included; Hundi/fund/festival, cancellation/refund UI, and 80G/FCRA issuance are deferred until their gates are implemented and tested.

Remaining Stage 3 gaps:

- Complete deployment-readiness review.
- Complete a production-readiness review for environment configuration, seed/demo tenant assumptions, audit retention, backup/restore expectations, and deployment rollback notes.
- Keep Hundi/fund/festival, cancellation/refund UI, and 80G/FCRA issuance out of the first live cut unless their documented gates are implemented and tested.

### Stage 4: GruhaMitra in MitraBooks ERP

Goal: validate housing society workflows inside the unified ERP shell.

Validate:

- Flats, towers, units, and resident lifecycle.
- Maintenance billing.
- Maintenance collections.
- Complaints/service requests where implemented.
- Vendor/parking flows where implemented.
- Maintenance posting through MitraBooks accounting.
- Tenant-scoped housing data.

Gate: GruhaMitra workflows work through the shared ERP shell without duplicating accounting logic.

### Stage 5: Combined MitraBooks ERP Regression

Goal: prove MitraBooks, MandirMitra, and GruhaMitra can coexist in the unified ERP shell.

Validate:

- Enabled modules and permissions drive navigation.
- Product names are not hardcoded as access rules.
- App context does not leak across workflows.
- Accounting reports remain correct after mixed workflow postings.
- Module-specific routes fail closed when module access is disabled.

Gate: the unified ERP can be maintained as one product surface.

### Stage 6: InvestMitra

Goal: validate InvestMitra after the ERP path is stable.

Validate:

- Portfolio and holding workflows.
- P&L and analytics workflows.
- Tenant-scoped investment data.
- Read-only external research integrations where implemented.
- No live trade placement, modification, cancellation, or automation.
- No broker tokens or financial data in logs.

Gate: InvestMitra remains a separate, read-safe investment product experience.

## Gap

The repo still needs stage-specific E2E checklists and scripts. Until those exist, use this plan as the manual validation order and record pass/fail notes per stage.

## Non-Goals

- Do not merge all frontends before staged E2E passes.
- Do not require InvestMitra E2E before MitraBooks ERP core is stable.
- Do not treat planned integrations as implemented.
- Do not troubleshoot all products in one combined pass unless each prior stage is already green.
