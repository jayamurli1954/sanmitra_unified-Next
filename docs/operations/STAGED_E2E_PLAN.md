# Staged E2E Plan

## Purpose

SanMitra E2E validation must be practical for a one-person platform owner. Do not attempt full-platform E2E across all products in one pass unless each stage below is already green.

The goal is to isolate failures, reduce troubleshooting load, and build confidence stage by stage.

## Current State

- LegalMitra is already tested and deployed live.
- MitraBooks ERP is the planned unified shell for MitraBooks, MandirMitra, and GruhaMitra workflows.
- InvestMitra remains a separate product experience.
- Full combined E2E across every product would create too much support and debugging surface for one maintainer.

## Target State

Each product area has a focused E2E checklist and a clear pass/fail gate. A later stage should not expand scope until the previous stage has passed its smoke and E2E checks.

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

Goal: prove the shared ERP/accounting foundation is stable before adding merged domain workflows.

Validate:

- Login and tenant context.
- `X-App-Key` handling.
- Module registry and enabled module rendering.
- Chart of Accounts.
- Journal posting.
- Ledger, trial balance, and financial reports.
- RBAC allow/deny checks.
- Idempotency for financial postings.
- Accounting invariant: debits equal credits.

Gate: MitraBooks ERP core can be trusted as the accounting and navigation foundation.

### Stage 3: MandirMitra in MitraBooks ERP

Goal: validate temple, trust, NGO, donation, and seva workflows inside the unified ERP shell.

Validate:

- Devotee management.
- Donation creation.
- Receipt generation.
- Seva booking.
- Hundi/festival flows where implemented.
- Donation and seva posting through MitraBooks accounting.
- Tenant-scoped temple data.

Gate: MandirMitra workflows work through the shared ERP shell without bypassing accounting.

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
