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

The existing backend in `D:\sanmitra-backend` is the reference implementation. It already contains:

- Unified FastAPI backend foundation.
- Modular monolith structure.
- MongoDB-backed users, tenants, and domain data.
- PostgreSQL accounting engine.
- Tenant middleware scaffold.
- RBAC foundation.
- `X-App-Key` based product routing.
- COA mapping APIs.
- MandirMitra donation posting into accounting.
- GruhaMitra maintenance collection posting into accounting.
- LegalMitra tenant-scoped route stubs.

The current frontend landscape is being consolidated for GruhaMitra, MandirMitra, MitraBooks, and LegalMitra only.

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

## Immediate Gap

Before frontend merging starts, the platform needs a small foundation PR:

- Formal `organization_type`.
- Formal `enabled_modules`.
- Module registry.
- Module/feature access checks.
- Tenant isolation tests.
- Accounting invariant tests.
- Clear migration documentation.

## Documentation Map

- [AGENTS.md](AGENTS.md) — mandatory guardrails for agents, accounting, tenancy, and destructive shell commands (§5)
- [Local CI & Security SOP](docs/LOCAL_CI_AND_SECURITY_SOP.md)
- [Unified Platform PRD](docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md)
- [MitraBooks ERP Gap Matrix](docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md)
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

## Non-Goals for First PR

The first PR must not include:

- Full frontend merge.
- Major UI redesign.
- Accounting engine rewrite.
- Microservices extraction.
- Replacing MongoDB/PostgreSQL strategy.
- Changes to live frontend applications.
