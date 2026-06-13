# Module Registry Design

## Purpose

The module registry is the source of truth for:

- Which modules exist.
- Which organization types can use them.
- Which app keys can expose them.
- Which subscription plans enable them.
- Which roles can access their actions.

## Registry Record

Suggested shape:

```json
{
  "module_key": "temple",
  "display_name": "MandirMitra Temple Operations",
  "allowed_organization_types": ["TEMPLE"],
  "allowed_app_keys": ["mandirmitra", "mitrabooks"],
  "minimum_plan": "pro",
  "default_enabled": true,
  "routes": ["/api/v1/temple"],
  "features": ["donations", "sevas", "hundi", "festival_accounting"]
}
```

## Core Modules

These are always available to active tenants:

- `auth`
- `users`
- `audit`
- `accounting` for accounting-capable tenants

## Product Modules

| module_key | Organization types | Notes |
| --- | --- | --- |
| `housing` | `HOUSING` | GruhaMitra workflows |
| `temple` | `TEMPLE` | MandirMitra workflows |
| `business` | `BUSINESS` | MitraBooks business workflows |
| `professional` | `PROFESSIONAL` | MitraBooks professional workflows |
| `legal` | `LEGAL` | LegalMitra workflows |
| `legal_ai` | `LEGAL` | Claude for Legal and legal assistant integrations |

InvestMitra modules are excluded from the SanMitra unified registry. Do not add `investment`, `portfolio`, `investment_research`, or `broker_research` to unified tenant entitlements unless the platform owner explicitly reverses the InvestMitra exclusion decision.

## Access Decision

An API route should allow access only when all are true:

- Tenant is active.
- User is authenticated.
- User belongs to tenant.
- Requested module is in `enabled_modules`.
- Current `app_key` is allowed for that module.
- User role has the required permission.
- Subscription plan includes the feature when applicable.

## First PR Implementation Target

The first implementation should add the registry and access helpers without refactoring all routes at once. Apply enforcement to one or two representative module routes first, then expand in later PRs.

## Integration Module Flags

External integrations should be feature/module gated separately from base products:

| module_key | Default | Reason |
| --- | --- | --- |
| `legal_ai` | Off | Requires confidentiality, legal-source, and lawyer-review workflow approval |
