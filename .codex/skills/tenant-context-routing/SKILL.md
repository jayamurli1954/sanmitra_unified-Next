---
name: tenant-context-routing
description: SanMitra tenant, app-key, organization-type, module access, RBAC, and route isolation workflow. Use when editing authentication, authorization, middleware, protected APIs, tenant services, module registry access, frontend app-context wiring, or any MongoDB/PostgreSQL query that reads or writes tenant-owned data.
---

# Tenant Context Routing

## Workflow

1. Identify the affected product context: `legalmitra`, `investmitra`, `mitrabooks`, `mandirmitra`, or `gruhamitra`.
2. Resolve trusted context from server-side auth/session/middleware, not request bodies.
3. Keep `tenant_id`, `app_key`, and `organization_type` separate.
4. Validate module access before returning module data.
5. Add or update tests for allow/deny behavior when the change touches protected data.

## Rules

- Never trust `tenant_id` from request body for protected routes.
- Treat `X-Tenant-ID` as privileged override only when explicitly super-admin gated and audited.
- Every MongoDB query on tenant-owned data must include tenant scope.
- Every PostgreSQL accounting row/query must include tenant scope.
- Every protected request must resolve role and permissions before domain access.
- Do not rely on hidden frontend menus as authorization.
- Shared/global data must be clearly marked as system-scoped and must not contain tenant-private data.

## Domain Boundaries

- LegalMitra may integrate billing, but legal documents and research stay tenant/app isolated.
- InvestMitra must never expose broker or portfolio data across tenants/users.
- MandirMitra and GruhaMitra collections may post accounting effects only through MitraBooks accounting services.
- MitraBooks shared accounting services must stay generic and must not embed temple, housing, legal, or investment rules.

## Completion Checklist

- State the tenant context source used by changed code.
- State which records are tenant-owned.
- Verify reads, writes, updates, deletes, background jobs, and reports are tenant-scoped.
- Verify app-key/module checks where the route is product/module-specific.
- Add cross-tenant denial tests where practical.
