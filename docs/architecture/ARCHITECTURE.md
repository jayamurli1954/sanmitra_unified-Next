# SanMitra Unified Architecture

## Architecture Style

SanMitra should remain a modular monolith at this stage.

This gives:

- One deployable backend.
- Shared authentication and tenancy.
- Shared accounting engine.
- Simpler debugging.
- Clear module boundaries without microservice overhead.

## Current Reference Backend

The reference backend is located at `D:\sanmitra-backend` and should be treated as read-only unless the user explicitly requests edits there.

Relevant current structure:

```text
app/
  main.py
  config.py
  api/v1/router.py
  core/
    auth/
    tenants/
    permissions/
    users/
    notifications/
    audit/
    billing/
  modules/
    temple/
    housing/
    legal/
  accounting/
    models/
    journal/
    ledger/
    reports/
    router.py
    schemas.py
    service.py
  db/
    mongo.py
    postgres.py
```

## Target Backend Shape

```text
app/
  core/
    auth/
    tenancy/
    permissions/
    users/
    module_registry/
    feature_flags/
    audit/
    billing/
  accounting/
    accounts/
    journal/
    ledger/
    reports/
    taxation/
    coa/
  modules/
    housing/
    temple/
    business/
    professional/
    legal/
  ai/
    rag/
    insights/
  db/
    mongo.py
    postgres.py
```

This is a target shape, not a required first PR restructuring.

## Database Strategy

### PostgreSQL

Use PostgreSQL only for accounting and financial data:

- Accounts.
- Journal entries.
- Journal lines.
- Ledger reports.
- Tax records.
- Financial invariants.

The PostgreSQL accounting layer must enforce double-entry accounting:

- Accounting equation: `Assets = Liabilities + Equity`.
- Journal postings must be atomic.
- Total debits must equal total credits before commit.
- Posted ledger rows are append-only.
- Reversals/adjustments are new entries, not edits to posted entries.
- Money must be stored as fixed-precision decimals or integer minor units, never floating-point values.

Account type behavior:

| Account type | Debit effect | Credit effect |
| --- | --- | --- |
| Asset | Increase | Decrease |
| Liability | Decrease | Increase |
| Equity | Decrease | Increase |
| Revenue | Decrease | Increase |
| Expense | Increase | Decrease |

### MongoDB

Use MongoDB for flexible domain and operational data:

- Tenants.
- Users.
- Module records.
- Residents.
- Devotees.
- Legal cases.
- Audit events.
- RAG documents.

## Request Context

Every protected request should resolve:

- `tenant_id`
- `app_key`
- `organization_type`
- `enabled_modules`
- user role and permissions

`tenant_id` must come from trusted auth context, not request bodies.

## App Keys vs Organization Types

`X-App-Key` identifies the product/application context:

- `gruhamitra`
- `mandirmitra`
- `mitrabooks`
- `legalmitra`

`organization_type` identifies the tenant's business category:

- `HOUSING`
- `TEMPLE`
- `BUSINESS`
- `PROFESSIONAL`
- `LEGAL`

Both are useful. Do not collapse them into one field.

## Frontend Direction

Target frontends:

- MitraBooks Unified ERP: handles GruhaMitra, MandirMitra, MitraBooks accounting workflows.
- LegalMitra: remains separate.
InvestMitra is excluded from SanMitra unified backend and deployment scope. It may be developed separately for personal use only.

The MitraBooks frontend should load menus and routes from API-provided module access, not hardcoded product assumptions.

## External Integration Architecture

External integrations must be wrapped behind internal adapters. Frontends should never call third-party tools directly with user credentials.

```text
frontend
  -> SanMitra API
    -> integration adapter
      -> external tool/provider
```

### LegalMitra Legal AI Adapter

Planned adapter:

- `claude_for_legal`: optional legal workflow assistant integration.

Rules:

- Preserve confidentiality and tenant isolation.
- Keep source attribution and citation verification.
- Do not represent AI output as final legal advice.
- Keep lawyer/user review in the workflow.
- Store prompts and responses only according to tenant policy and legal confidentiality requirements.
