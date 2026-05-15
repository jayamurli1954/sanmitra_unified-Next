# AGENTS.md - SanMitra Unified Next Guardrails & Architecture Policy

This file is mandatory operating policy for AI coding assistants working in this workspace.

## 1. Workspace Scope

### Editable Workspace

All active work must happen inside:

```text
D:\sanmitra_unified-Next
```

This workspace is for the next unified SanMitra platform foundation, documentation, copied backend foundation work, and later incremental implementation.

### Reference-Only Backend

The existing backend may be read for reference from:

```text
D:\sanmitra-backend
```

Use it for:

- Existing architecture and route patterns.
- Existing schemas, services, tests, migrations, and docs.
- Existing `AGENTS.md` guardrails.
- Existing README and module behavior.

Do not edit `D:\sanmitra-backend` unless the user explicitly asks.

### C Drive Restriction

Do not use `C:\` for project source, generated project files, copied backend code, or persistent project artifacts. Temporary tool/runtime internals may exist there, but SanMitra project work belongs in `D:\sanmitra_unified-Next`.

## 2. Product Branding

Use these product names exactly:

- GruhaMitra
- MandirMitra
- MitraBooks
- LegalMitra
- InvestMitra

Do not use `GharMitra` or `GrihaMitra` in new documentation or code. If reference material contains old spellings, normalize to `GruhaMitra` unless quoting legacy text.

API compatibility may still require existing lowercase app keys:

- `gruhamitra`
- `mandirmitra`
- `mitrabooks`
- `legalmitra`
- `investmitra`

## 3. Platform Direction

SanMitra is moving from five separate product frontends toward three frontend experiences:

| Frontend | Scope |
| --- | --- |
| MitraBooks Unified ERP | GruhaMitra, MandirMitra, and MitraBooks accounting/business workflows |
| LegalMitra | Legal research, legal workflow, RAG, compliance |
| InvestMitra | Investment, portfolio, screening, analytics |

The backend direction is a modular monolith with a shared accounting engine.

## 4. Current vs Target Discipline

Every implementation plan, document, and PR must distinguish:

- Current state: what exists now in the reference backend.
- Target state: the planned unified platform direction.
- Gap: what must be built before the target can be treated as real.
- Deferred scope: what must not be included in the current PR.

Do not write docs or code as if planned features already exist. Use explicit language such as `planned`, `target`, `gap`, `phase`, or `not yet implemented`.

## 5. Repository and Import Rules

### Copying From Reference Backend

Copy intentionally from `D:\sanmitra-backend`.

Allowed:

- Architecture docs.
- Route and service patterns.
- Schemas and tests needed for the new foundation.
- AGENTS/README guidance.
- Migration examples.
- Module-level implementation that is deliberately being moved into this workspace.

Forbidden unless explicitly approved:

- `.env` or `.env.*`.
- `.venv`, `venv`, `.pgdata`, `.pytest_cache`, `htmlcov`, logs, tmp, artifacts.
- Local database files or runtime-generated output.
- Secrets, tokens, API keys, credentials.
- Live frontend repositories or deployment artifacts.

### Git Safety

If this workspace becomes a git repository:

- Never run `git add .` from repo root.
- Stage explicit paths only.
- Never commit secrets.
- Never rewrite history on shared branches.
- Never revert user changes unless explicitly requested.

## 6. Data Layer Ownership

The target is one unified backend platform with a split database strategy, not one physical database.

| Store | Ownership |
| --- | --- |
| PostgreSQL | Accounting data: accounts, journals, journal lines, ledger, financial reports, tax records |
| MongoDB | Tenants, users, module/domain data, residents, devotees, legal cases, investment holdings, audit records, RAG documents |
| Redis | Cache, sessions, background job coordination where applicable |

PostgreSQL must remain the source of truth for financial postings. MongoDB must remain flexible domain storage.

## 7. Multi-Tenancy and App Context

Every protected request must resolve trusted context:

- `tenant_id`
- `app_key`
- `organization_type`
- `enabled_modules`
- user role
- user permissions

Rules:

- Never trust `tenant_id` from request body for protected routes.
- Every MongoDB query must be tenant-scoped.
- Every PostgreSQL accounting row must be tenant-scoped.
- Every module route must validate module access before returning tenant data.
- `X-App-Key` must be validated and fail gracefully when missing/invalid.
- Super-admin tenant override, if present, must be explicit and audited.

Do not collapse `app_key` and `organization_type`. They answer different questions:

- `app_key`: which product/application context is calling.
- `organization_type`: what type of organization the tenant is.

## 8. First PR Scope

The first PR in this workspace should be foundation-focused only.

Allowed:

- Documentation cleanup and alignment.
- Current vs target matrix.
- `organization_type` enum/design.
- `enabled_modules` design.
- Module registry design or initial implementation.
- Feature flag and module access design.
- Tenant isolation and module access test plan.
- Small representative access helper implementation, if code is introduced.

Not allowed in the first PR:

- Full frontend merge.
- Major UI redesign.
- Accounting engine rewrite.
- Large database redesign.
- Microservices extraction.
- Production data migration.
- Live app repository changes.

## 9. Module Registry Policy

The module registry is the source of truth for:

- Module key.
- Display name.
- Allowed organization types.
- Allowed app keys.
- Minimum subscription plan.
- Default enabled state.
- Feature list.
- Route group.

An access decision should require:

- Active tenant.
- Authenticated user.
- User belongs to tenant.
- Requested module is enabled for tenant.
- Current app key is allowed for module.
- Role has permission.
- Subscription includes feature where applicable.

## 10. Accounting Guardrails - MitraBooks

MitraBooks is the shared accounting engine and must protect double-entry integrity.

### Accounting Doctrine

The accounting engine must strictly follow double-entry accounting without deviation.

Every financial transaction must affect at least two accounts through equal and opposing debit and credit entries. The core accounting equation must always hold:

```text
Assets = Liabilities + Equity
```

Core rules:

- Debits must equal credits.
- No orphaned ledger lines.
- No direct balance updates without journal entries.
- Ledger entries are append-only; use reversals or soft-delete/audit where needed.
- Every account must belong to the tenant.
- Financial posting endpoints should support idempotency.
- Accounting logic must not be duplicated inside GruhaMitra, MandirMitra, business, legal, or investment modules.
- Use high-precision amount storage. Do not use floating-point types for money. Use integer minor units or fixed-precision decimal types.
- Wrap every posting in one database transaction so all debit and credit lines succeed or fail together.
- Validate `sum(debits) - sum(credits) = 0` before committing any entry.
- Posted transactions must be immutable. Do not update or delete posted ledger entries; reverse them with a new journal entry.

### Modern Account Types

| Account type | Meaning | Debit effect | Credit effect |
| --- | --- | --- | --- |
| Asset | Economic resources owned, such as cash, bank, inventory, receivables | Increase | Decrease |
| Liability | Obligations owed to outsiders, such as loans and accounts payable | Decrease | Increase |
| Equity | Owner/trust residual interest after liabilities | Decrease | Increase |
| Revenue | Income generated from operations, donations, services, sales, fees | Decrease | Increase |
| Expense | Costs incurred to operate or generate revenue | Increase | Decrease |

### Traditional Golden Rules

| Traditional type | Meaning | Golden rule |
| --- | --- | --- |
| Real accounts | Tangible or intangible property and possessions, such as cash, buildings, machinery, patents | Debit what comes in, credit what goes out |
| Personal accounts | Individuals, companies, institutions, banks, debtors, creditors, capital accounts | Debit the receiver, credit the giver |
| Nominal accounts | Income, gains, expenses, and losses | Debit all expenses and losses, credit all incomes and gains |

### Non-Negotiable Posting Requirements

1. Atomicity: every journal posting must run inside one database transaction block.
2. Balance validation: reject the posting unless total debits equal total credits exactly.
3. Immutability: posted entries are append-only and can only be corrected by reversal/adjustment entries.
4. Precision: money must use integer minor units or fixed-precision decimals, never binary floating point.
5. Auditability: every posting must retain tenant, source module, source document/reference, actor, timestamp, and reversal link where applicable.

Required posting pattern:

```python
def post_transaction(tenant_id, debit_account, credit_account, amount, description):
    # 1. Validate tenant and both accounts
    # 2. Validate amount, currency, and posting date
    # 3. Ensure debit equals credit
    # 4. Create journal entry and journal lines atomically
    # 5. Write audit event
    # 6. Return stable posting reference
    pass
```

Forbidden:

- Raw PostgreSQL inserts/updates for accounting outside the accounting service.
- Direct account balance mutation without ledger entry.
- Posting domain-specific transactions without a GL reference.
- Deleting accounting records without audit and reversal strategy.
- Using `float`/`double` for financial amounts.
- Partially committing only one side of a journal entry.
- Editing a posted journal entry in place.

## 11. GruhaMitra Guardrails

GruhaMitra covers housing society workflows.

Core areas:

- Flats, towers, blocks, units.
- Residents and ownership/occupancy lifecycle.
- Maintenance billing and collection.
- Complaints/service requests.
- Parking and vendor payments.
- Society accounting.

Rules:

- Society/tenant isolation is mandatory.
- Maintenance collections must post through MitraBooks accounting.
- Notices, complaints, and financial actions need audit trail.
- Do not embed housing-specific rules in the shared accounting engine.
- Use `organization_type = HOUSING`.
- Use app key `gruhamitra` for compatibility where needed.

## 12. MandirMitra Guardrails

MandirMitra covers temple, trust, NGO, donation, and seva workflows.

Core areas:

- Donations.
- Receipts.
- Hundi collections.
- Seva booking.
- Devotees.
- Festivals.
- Trust/corpus accounting.
- 80G readiness where applicable.

Rules:

- Donation receipt generation must not be skipped.
- Donation and seva collections must post through MitraBooks accounting.
- Do not hardcode country/currency unless the tenant configuration requires it.
- Receipt numbering must be stable and auditable.
- Domain records live in MongoDB; financial postings live in PostgreSQL.
- Use `organization_type = TEMPLE`.

## 13. LegalMitra Guardrails

LegalMitra remains a separate product experience.

Core areas:

- Legal cases.
- Documents.
- Compliance calendar.
- RAG and legal research.
- Client billing integration where needed.

RAG rules:

- Never return legal research without source attribution.
- Never hallucinate case numbers, statute sections, or court references.
- Include retrieval/source dates where live or changing law is involved.
- Keep tenant/app isolation for documents and retrieval.
- Flag stale or uncertain legal data.

LegalMitra may integrate with accounting for billing, but it should not become part of the MitraBooks unified ERP frontend unless explicitly decided later.

### Claude for Legal Integration

Claude for Legal is a planned LegalMitra enhancement, not first-PR scope.

Rules:

- Preserve client confidentiality.
- Keep legal-source attribution.
- Never present model output as final legal advice.
- Require human review for drafting, research, and filing workflows.
- Do not send confidential tenant documents to external providers unless tenant policy and user authorization allow it.
- Store prompts/responses only according to tenant retention and confidentiality policy.

## 14. InvestMitra Guardrails

InvestMitra remains a separate product experience.

Core areas:

- Portfolio holdings.
- Asset classes.
- P&L and XIRR.
- Screening and analytics.
- Optional broker/API integrations.

Rules:

- Never execute live trades from test or development workflows.
- Trading/broker tokens must never be logged.
- Investment data must be tenant-scoped.
- Aggregated P&L should be reproducible from source transactions/holdings.
- Keep InvestMitra frontend separate from MitraBooks Unified ERP.

### InvestMitra External Research Integrations

Planned integrations:

- FinceptTerminal: investment research, financial analytics, macro/economic data, and report generation.
- Zerodha Kite MCP: authenticated market/portfolio context for research.

Rules:

- These integrations are for investment research only.
- Never place, modify, cancel, or automate trades.
- Do not expose order execution tools in UI or backend adapters.
- Do not call broker APIs directly from frontend code.
- Do not log broker credentials, access tokens, request tokens, holdings exports, or personal financial data.
- Every request must be tenant-scoped and user-authorized.
- Every research output must show source and timestamp where available.
- Check FinceptTerminal licensing before internal/commercial use.

## 15. Authentication and Authorization

Rules:

- Use `Authorization: Bearer <token>` for protected APIs.
- Do not accept tokens in request bodies.
- Passwords must be hashed with approved hashing.
- Refresh tokens, if used, must be server-controlled and revocable.
- RBAC must be enforced at route/module/feature level.
- Module access must not rely only on hidden frontend menu items.

## 16. API Standards

All APIs should follow:

- Versioned routes under `/api/v1`.
- Tenant-safe behavior.
- Consistent error envelopes.
- Pagination for list endpoints.
- Idempotency for financial POST operations.
- Clear request/response schemas.
- No frontend-specific business logic inside backend handlers.

Headers:

- `Authorization: Bearer <access_token>`
- `X-App-Key: <app_key>`
- `X-Idempotency-Key` for financial posting where applicable.
- `X-Tenant-ID` only for explicit super-admin support override, if implemented.

## 17. Cross-Database Consistency

Some workflows write to MongoDB and PostgreSQL.

Rules:

- Prefer a clear transaction boundary where possible.
- If using compensating rollback, document failure modes.
- Financial posting failure must not leave a completed-looking domain transaction.
- Long-term target should consider outbox/event-log patterns for reliability.
- Every cross-db workflow needs tests for accounting failure and rollback/compensation behavior.

## 18. Testing Policy

Test depth should match risk.

Mandatory test categories for foundation work:

- Tenant isolation.
- App-key isolation.
- Module registry access allow/deny.
- RBAC allow/deny.
- Accounting debit-credit invariant.
- Idempotency on financial posting.
- Cross-db failure behavior for donation/maintenance flows.

Suggested commands once code exists:

```powershell
python -m compileall app scripts tests
python -m pytest tests/accounting -v
python -m pytest tests/modules -v
python -m pytest -q
```

If this workspace does not yet have runnable code, document that tests are not available rather than pretending validation passed.

## 19. Documentation Standards

Docs must be practical and implementation-ready.

Every major doc should state:

- Current state.
- Target state.
- Gap.
- Implementation sequence.
- Non-goals.

Every module should eventually have:

- Purpose.
- Key workflows.
- Data ownership.
- Main endpoints.
- Accounting integration points.
- Tenant isolation rules.
- Test expectations.

## 20. Frontend Merge Policy

Do not merge all frontends in one step.

Sequence:

1. Backend readiness: `organization_type`, `enabled_modules`, module registry, access checks.
2. MitraBooks unified shell.
3. Shared accounting dashboard.
4. Migrate MitraBooks business workflows.
5. Migrate GruhaMitra housing workflows.
6. Migrate MandirMitra temple workflows.
7. Keep LegalMitra and InvestMitra separate.

Frontend rule:

```text
Render UI based on enabled modules and permissions, not hardcoded product names.
```

## 21. Security Rules

Never commit or copy:

- `.env`
- API keys.
- JWT secrets.
- Database passwords.
- Razorpay credentials.
- Broker credentials.
- Legal source API keys.
- User PII exports.
- Database dumps.

Never log:

- Passwords.
- Tokens.
- Payment details.
- Broker credentials.
- Sensitive legal documents.
- Personal financial data.

## 22. Emergency Procedures

If a change risks accounting, tenant isolation, payment receipts, legal data, or investment data:

1. Stop.
2. Identify affected module and tenants.
3. Document risk and rollback path.
4. Do not proceed with broad refactor.
5. Ask the user before risky or destructive actions.

Critical labels to use in notes/issues:

- `[CRITICAL-ACCOUNTING]`
- `[CRITICAL-TENANCY]`
- `[CRITICAL-LEGAL]`
- `[CRITICAL-PAYMENT]`
- `[CRITICAL-INVESTMENT]`
- `[CRITICAL-SECURITY]`

## 23. Validation Before Final Response

Before reporting work complete:

- Confirm files changed are only under `D:\sanmitra_unified-Next`.
- Mention if `D:\sanmitra-backend` was read as reference.
- Mention if no tests were run because this workspace has docs only.
- Mention any remaining ambiguity or implementation risk.

## 24. Version History

| Version | Date | Changes |
| --- | --- | --- |
| 1.0 | 2026-05-15 | Initial workspace policy for SanMitra unified next foundation |
| 1.1 | 2026-05-15 | Expanded with backend guardrails, module-specific policies, testing, security, and frontend merge rules |
