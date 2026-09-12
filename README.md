# SanMitra Unified Next

This workspace is for the next unified SanMitra platform foundation. It is separate from the live/reference backend at `D:\sanmitra-backend`.

## Product Scope

SanMitra unified backend currently includes four product brands:

- GruhaMitra
- MandirMitra
- MitraBooks
- LegalMitra

InvestMitra is excluded from the SanMitra unified backend and deployment scope. It may be developed separately for personal use only.

The target platform keeps the four active unified brands and reduces accounting frontend duplication.

## Live Domain And App Context Map

The four live product domains share the unified backend and the same MongoDB/PostgreSQL
data stores. `X-App-Key` identifies the product context for authorization and module
routing; it does not select a separate database.

| Live domain | Product context | `X-App-Key` | Accounting model |
| --- | --- | --- | --- |
| `www.legalmitra.sanmitratech.in` | LegalMitra legal workflows | `legalmitra` | Legal data is tenant/app isolated; billing can integrate with accounting where enabled. |
| `www.gruhamitra.sanmitratech.in` | GruhaMitra housing workflows | `gruhamitra` | Housing financial workflows post through the shared MitraBooks double-entry engine. |
| `www.mandirmitra.sanmitratech.in` | MandirMitra temple/trust workflows | `mandirmitra` | Temple financial workflows post through the shared MitraBooks double-entry engine. |
| `www.mitrabooks.sanmitratech.in` | MitraBooks unified ERP shell | `mitrabooks` by default; switches to `mandirmitra`/`gruhamitra` for those experiences | Shared double-entry accounting engine. |

## Current State

`D:\sanmitra_unified-Next` is the active unified backend and ERP shell. `D:\sanmitra-backend` is reference-only.

This workspace already contains:

- Modular FastAPI monolith with `organization_type`, `enabled_modules`, module registry, RBAC, and `X-App-Key` product context.
- Shared PostgreSQL accounting engine (journals, ledger, trial balance, P&L, balance sheet, receipts and payments, reversal, idempotency).
- MongoDB for tenants, users, and domain records. Every protected query must stay tenant-scoped.
- MitraBooks ERP shell at `www.mitrabooks.sanmitratech.in` hosting business, MandirMitra, and GruhaMitra experiences.
- MitraBooks business slices under `/api/v1/business`: parties (including `customer | vendor | both`), typed vouchers, sales invoices, purchase bills, credit/debit notes, cash AR/AP allocation, GST/TDS **preparation** reports, inventory (weighted-average periodic), bank reconciliation, fixed assets, dimensions, opening balances, year-end close, MIS, data health, and CA practice client books.
- MandirMitra donation, seva, public payment, receipt, hundi/fund, and 80G-readiness paths posting through the shared accounting engine.
- GruhaMitra maintenance billing and collection posting through the same engine.

These slices are **live on the unified domains** (`www.mitrabooks.sanmitratech.in` and the shared backend). Remaining work is operator/compliance **signoff** and a few unfinished workflows — not a second deploy. GST outputs are preparation/reporting until a CA signs filing. Live IRP/e-way, live bank APIs, OCR auto-post, and InvestMitra remain out of unified scope.

Detailed current vs target: [MitraBooks ERP Gap Matrix](docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md) and [Current vs Target](docs/architecture/CURRENT_VS_TARGET.md).

## Target State

The target is a unified platform with two deployable frontend experiences:

- MitraBooks unified ERP frontend, covering:
  - GruhaMitra housing society workflows.
  - MandirMitra temple and trust workflows.
  - MitraBooks business, SME, and professional accounting workflows.
- LegalMitra separate frontend.

The accounting engine remains shared. Domain modules remain modular.

## Key Design Decision

This is not one physical database.

The target is one unified backend platform with a split database strategy:

- PostgreSQL: accounting, ledger, journals, reports, tax, financial invariants.
- MongoDB: tenants, users, module data, operational records, legal data, audit records.

## Remaining Gaps

Foundation work (`organization_type`, module registry, isolation tests, accounting invariants) is in place and live. What remains is **signoff and unfinished workflows**, not a missing deploy:

- Hosted destructive mutation **reconfirm** on `demo-mitrabooks-business` after staging credential drift.
- MandirMitra opt-in **demo-tenant** mutation and production signoff (donation/seva/refund/fund).
- GST/TDS **human compliance** review. Keep outputs labeled preparation until signed. Live GST IRP/e-way bill APIs stay deferred.
- GruhaMitra housing unit/resident lifecycle and remaining society workflows in the ERP shell.
- Print/PDF polish, CA staff-per-book assignment, pricing client caps, and operator maker-checker signoff for opening/year-end.
- AR/AP netting / set-off is **not implemented** (planned Phase 4 completeness; dual-role party already exists).

Do not treat provider configuration shells as live integrations.

## Documentation Map

- [AGENTS.md](AGENTS.md) — mandatory guardrails for agents, accounting, tenancy, and destructive shell commands (§5)
- [Local CI & Security SOP](docs/LOCAL_CI_AND_SECURITY_SOP.md)
- [GST/TDS compliance review](docs/operations/MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md)
- [Unified Platform PRD](docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md)
- [MitraBooks ERP Gap Matrix](docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md)
- [MitraBooks Completion Roadmap](docs/prd/MITRABOOKS_COMPLETION_ROADMAP.md)
- [MitraBooks Pending Gap Todo](docs/operations/MITRABOOKS_PENDING_GAP_TODO.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Current vs Target Matrix](docs/architecture/CURRENT_VS_TARGET.md)
- [Accounting Doctrine](docs/architecture/ACCOUNTING_DOCTRINE.md)
- [External Integrations](docs/architecture/EXTERNAL_INTEGRATIONS.md)
- [Module Registry](docs/architecture/MODULE_REGISTRY.md)
- [Frontend Merge Plan](docs/migration/FRONTEND_MERGE_PLAN.md)
- [Foundation PR Plan](docs/migration/FOUNDATION_PR_PLAN.md)
- [Staged E2E Plan](docs/operations/STAGED_E2E_PLAN.md)
- [Naming Conventions](docs/standards/NAMING_CONVENTIONS.md)
- [Release and Rollback Runbook](docs/operations/RELEASE_AND_ROLLBACK.md)

## CI/CD and Versioning

- `backend-ci` runs repository safety checks, compile checks, route-contract checks, and pytest.
- `codeql-analysis` runs GitHub CodeQL static security analysis for Python.
- `security-trivy` runs dependency, secret, and misconfiguration scanning.
- `release-tag` creates versioned fallback points after release preflight passes.
- `render-deploy` deploys manually to staging or production.

Production releases must use tags like `backend-v1.2.3`, matching the `VERSION` file. Rollback should use the previous known-good `backend-v*` tag, not an arbitrary branch head.

## Architecture Non-Goals

Do not include in unified MitraBooks ERP delivery:

- Accounting engine rewrite or microservices extraction.
- Replacing the MongoDB/PostgreSQL split.
- Desktop Electron, SQLite, or hardware-locked licensing.
- Live GST IRP/e-way bill APIs, live bank payout execution, or OCR/AI auto-post to the ledger until a named workstream and tenant policy exist.
- InvestMitra in unified backend, billing, E2E, or deploy.
