# ADR-004: `tenant_id` is the canonical tenancy identifier

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** SanMitra unified platform  

## Context

Some OfficeMitra drafts used `organization_id` for multi-tenancy. The platform already resolves trusted context with `tenant_id`, `app_key`, `organization_type`, `enabled_modules`, role, and permissions.

## Decision

- Use **`tenant_id`** as the only tenancy key for OfficeMitra documents, queries, connectors, and audit events.
- Do **not** introduce a parallel `organization_id` tenancy model.
- Every protected OfficeMitra request must use trusted middleware context — never trust `tenant_id` from the request body.
- Daily Brief and other cross-product features must gate connector calls on the tenant’s **`enabled_modules`** (and allowed `app_key`), not assume every tenant has every product.

## Consequences

- Mongo documents: `{ tenant_id, ... }`.
- Indexes: compound keys that always include `tenant_id`.
- Connector signatures take `tenant_id` (and any needed user/role context), not a separate org id.
