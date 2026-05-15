# SanMitra Unified Next

This workspace is for the next unified SanMitra platform foundation. It is separate from the live/reference backend at `D:\sanmitra-backend`.

## Product Scope

SanMitra has five product brands:

- GruhaMitra
- MandirMitra
- MitraBooks
- LegalMitra
- InvestMitra

The target platform keeps all five brands, but reduces accounting frontend duplication.

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
- LegalMitra and InvestMitra tenant-scoped route stubs.

The current frontend landscape still treats GruhaMitra, MandirMitra, MitraBooks, LegalMitra, and InvestMitra as separate products.

## Target State

The target is a unified platform with three frontend experiences:

- MitraBooks unified ERP frontend, covering:
  - GruhaMitra housing society workflows.
  - MandirMitra temple and trust workflows.
  - MitraBooks business, SME, and professional accounting workflows.
- LegalMitra separate frontend.
- InvestMitra separate frontend.

The accounting engine remains shared. Domain modules remain modular.

## Key Design Decision

This is not one physical database.

The target is one unified backend platform with a split database strategy:

- PostgreSQL: accounting, ledger, journals, reports, tax, financial invariants.
- MongoDB: tenants, users, module data, operational records, legal data, investment data, audit records.

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

- [Unified Platform PRD](docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Current vs Target Matrix](docs/architecture/CURRENT_VS_TARGET.md)
- [Accounting Doctrine](docs/architecture/ACCOUNTING_DOCTRINE.md)
- [External Integrations](docs/architecture/EXTERNAL_INTEGRATIONS.md)
- [Module Registry](docs/architecture/MODULE_REGISTRY.md)
- [Frontend Merge Plan](docs/migration/FRONTEND_MERGE_PLAN.md)
- [Foundation PR Plan](docs/migration/FOUNDATION_PR_PLAN.md)
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
