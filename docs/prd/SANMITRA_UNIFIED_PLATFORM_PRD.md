# SanMitra Unified Platform PRD

## Purpose

Create a clear foundation for merging the accounting-heavy product experiences into one maintainable ERP platform while preserving SanMitra's product brands.

## Product Brands

- GruhaMitra: housing societies, apartments, RWAs, gated communities.
- MandirMitra: temples, trusts, NGOs, donation and seva workflows.
- MitraBooks: businesses, SMEs, professionals, retailers, accounting users.
- LegalMitra: legal research, legal workflow, compliance.
- InvestMitra: portfolio tracking and investment intelligence.

## Current State

The reference backend at `D:\sanmitra-backend` already provides a unified backend foundation:

- One FastAPI backend.
- Modular monolith structure.
- Shared accounting engine.
- PostgreSQL for accounting records.
- MongoDB for tenant, user, and domain records.
- Tenant middleware scaffold.
- RBAC foundation.
- `X-App-Key` routing for product context.
- COA mapping APIs.
- MandirMitra donation accounting flow.
- GruhaMitra maintenance accounting flow.
- LegalMitra and InvestMitra tenant-scoped route stubs.

Current limitation: accounting-oriented frontends are still treated as separate product applications, creating duplicate UI and support effort.

## Target State

Move to three frontend experiences:

| Frontend | Scope |
| --- | --- |
| MitraBooks Unified ERP | GruhaMitra, MandirMitra, MitraBooks business/professional workflows |
| LegalMitra | Legal workflow and RAG product experience |
| InvestMitra | Investment and portfolio product experience |

The unified MitraBooks frontend should dynamically show modules based on organization type, subscription plan, user role, and feature access.

## Strategic Goals

- Reduce duplicated accounting UI.
- Keep one shared accounting engine.
- Keep tenant and product isolation explicit.
- Allow each organization to activate only relevant modules.
- Preserve brand-specific terminology where it improves user experience.
- Keep LegalMitra and InvestMitra separate because their workflows are not primarily accounting ERP workflows.

## Organization Types

Use these canonical values:

| organization_type | Primary frontend | Default modules |
| --- | --- | --- |
| `HOUSING` | MitraBooks Unified ERP | `housing`, `accounting`, `audit` |
| `TEMPLE` | MitraBooks Unified ERP | `temple`, `accounting`, `audit` |
| `BUSINESS` | MitraBooks Unified ERP | `business`, `accounting`, `gst`, `inventory`, `audit` |
| `PROFESSIONAL` | MitraBooks Unified ERP | `professional`, `accounting`, `billing`, `audit` |
| `LEGAL` | LegalMitra | `legal`, `rag`, `compliance`, `legal_ai`, `audit` |
| `INVESTMENT` | InvestMitra | `investment`, `portfolio`, `investment_research`, `broker_research`, `audit` |

## Functional Requirements

### Shared Platform

- Tenant onboarding and lifecycle.
- User and role management.
- App-key validation.
- Module registry.
- Feature/module access enforcement.
- Audit log.
- Subscription and plan readiness.

### Accounting Engine

- Chart of Accounts.
- Journal entry posting.
- Double-entry validation.
- Strict accounting equation enforcement: `Assets = Liabilities + Equity`.
- Modern account type behavior for Assets, Liabilities, Equity, Revenue, and Expenses.
- Traditional golden-rule support for Real, Personal, and Nominal accounts.
- Atomic posting of every journal entry.
- Immutable append-only posted ledger.
- High-precision amount handling with fixed decimals or integer minor units; no floating-point money.
- Ledger.
- Trial Balance.
- Profit and Loss.
- Balance Sheet.
- Income and Expenditure.
- Receipts and Payments.
- GST/TDS readiness.
- Idempotency for financial posting endpoints.

### Accounting Engine Non-Negotiables

The shared accounting engine must strictly follow double-entry accounting:

- Every financial transaction must have equal debits and credits.
- Validate `sum(debits) - sum(credits) = 0` before commit.
- Wrap debit and credit posting in one database transaction.
- Posted entries must not be edited or deleted.
- Corrections must use reversing or adjusting entries.
- Amounts must use high-precision storage, never floating-point types.

Modern account behavior:

| Account type | Debit | Credit |
| --- | --- | --- |
| Asset | Increase | Decrease |
| Liability | Decrease | Increase |
| Equity | Decrease | Increase |
| Revenue | Decrease | Increase |
| Expense | Increase | Decrease |

Traditional golden rules:

| Traditional type | Rule |
| --- | --- |
| Real accounts | Debit what comes in, credit what goes out |
| Personal accounts | Debit the receiver, credit the giver |
| Nominal accounts | Debit all expenses and losses, credit all incomes and gains |

### GruhaMitra Module

- Flats, towers, residents.
- Maintenance billing and collection.
- Parking and vendor payments.
- Complaint/service request lifecycle.
- Society accounting reports.

### MandirMitra Module

- Donations and receipts.
- Seva booking.
- Hundi collection.
- Devotee database.
- Trust/corpus/festival accounting.
- 80G readiness where applicable.

### MitraBooks Business Module

- Customers and vendors.
- Sales and purchases.
- GST invoices.
- Inventory.
- Payroll readiness.
- Business reports and MIS.

### LegalMitra

- Case records.
- Legal documents.
- RAG with source attribution.
- Compliance calendar.
- Claude for Legal integration readiness.
- Client billing integration where needed.

### InvestMitra

- Holdings.
- Asset classes.
- Portfolio performance.
- XIRR/P&L calculations.
- Investment insights.
- FinceptTerminal research integration readiness.
- Zerodha Kite MCP research integration readiness.

InvestMitra integrations are for investment research only. They must not place, modify, cancel, or automate trades.

## Non-Functional Requirements

- Tenant isolation on every query.
- Accounting immutability and auditability.
- API-first behavior.
- Modular monolith structure.
- Clear migration path.
- No live frontend disruption during migration.

## Explicit Non-Goals for Foundation PR

- Do not merge all frontends.
- Do not redesign the entire UI.
- Do not rewrite the accounting engine.
- Do not migrate production data.
- Do not create microservices.
- Do not change live app repositories.
- Do not implement FinceptTerminal production integration.
- Do not implement Zerodha Kite MCP production integration.
- Do not implement Claude for Legal production integration.

## Strategic Integration Roadmap

These integrations were discussed earlier and are now reserved in the product roadmap. They are planned incremental enhancements, not first-PR scope.

### InvestMitra: FinceptTerminal

Purpose:

- Use FinceptTerminal as a research and analytics source for InvestMitra.
- Support equity research, macro/economic research, portfolio analytics, screeners, and AI-assisted research summaries.

Boundary:

- Research only.
- No broker execution.
- No order placement, modification, cancellation, or automated trading.
- Licensing must be reviewed before any internal or commercial use.

### InvestMitra: Zerodha Kite MCP

Purpose:

- Use Zerodha Kite MCP only for authenticated, user-authorized market and portfolio context.
- Support holdings-aware research, watchlist enrichment, instrument lookup, quotes, and historical data where allowed.

Boundary:

- Read-only research use.
- Disable or omit all order placement tools.
- No financial advice framed as guaranteed outcome.
- Broker credentials and tokens must never be logged.

### LegalMitra: Claude for Legal

Purpose:

- Evaluate Claude for Legal as an optional LegalMitra assistant layer for legal drafting, review, research workflow, summarization, and document analysis.

Boundary:

- Preserve client confidentiality.
- Maintain source attribution.
- Do not replace lawyer/user review.
- Clearly distinguish retrieved legal source material from AI-generated analysis.
- Support Indian legal workflow and jurisdiction metadata before production use.

## Integration Sequence

1. Document capability, licensing, security, and compliance requirements.
2. Create adapter interfaces with no UI dependency.
3. Build read-only proof of concept.
4. Add audit logging and permission checks.
5. Add frontend read-only research/legal-assistant screens.
6. Add human-review workflows and disclaimers.
7. Enable per tenant/plan only after security and workflow review.
