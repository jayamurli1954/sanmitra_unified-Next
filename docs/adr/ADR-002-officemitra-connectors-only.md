# ADR-002: OfficeMitra AI communicates only through connectors

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** OfficeMitra AI  

## Context

OfficeMitra needs cross-product insights (revenue, overdue invoices, pending legal docs, maintenance requests). Direct imports of other modules’ repositories or raw collection access would couple products and break independently maintainable boundaries.

## Decision

OfficeMitra talks to other SanMitra products **only** through thin connector modules that call each product’s **existing service layer** (or stable internal API helpers), returning plain data structures (dicts/JSON-shaped results).

```text
OfficeMitra service → connector → product service → JSON-shaped result
```

Connectors expose small, intentional interfaces (for example `get_overdue_invoices(tenant_id)`), not raw ORM/SQL/Mongo queries.

## Consequences

- Schema changes inside MitraBooks/LegalMitra/etc. update only the connector.
- Stub connectors that return `[]` are valid until the product service surface is ready.
- Connector calls must respect `tenant_id`, `app_key`, and `enabled_modules`.
- No OfficeMitra service may import another product’s Mongo collection constants or Postgres models for ad-hoc queries.
