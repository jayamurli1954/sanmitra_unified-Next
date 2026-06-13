# Foundation PR Plan

## Goal

Prepare the backend and documentation for later frontend consolidation without touching live frontend applications or rewriting accounting.

## Scope

### Documentation

- Normalize branding to `GruhaMitra`, `MandirMitra`, `MitraBooks`, and `LegalMitra` for unified scope. Mark InvestMitra as separate personal-use scope.
- Clearly separate current state, target state, and gap.
- Document module registry and organization type strategy.
- Document frontend merge sequence.

### Backend Foundation

- Add `organization_type` to tenant model/design.
- Add `enabled_modules` to tenant model/design.
- Add module registry service.
- Add module access helper.
- Add tests for module access rules.
- Add tenant isolation tests where missing.
- Reserve feature/module flags for future LegalMitra integrations:
  - `legal_ai`

## Out of Scope

- Full frontend merge.
- Production data migration.
- Accounting engine rewrite.
- Large route renaming.
- Microservices extraction.
- Changes to `D:\sanmitra-backend` unless explicitly requested.
- InvestMitra, FinceptTerminal, or Zerodha Kite MCP integration in SanMitra unified backend.
- Claude for Legal production integration.

These three integrations should be documented and reserved in the module registry, but implemented only after the core foundation is stable.

## Suggested Implementation Order

1. Copy/reference existing backend guardrails into this workspace.
2. Add docs and align naming.
3. Add `organization_type` design and enum.
4. Add module registry.
5. Add `enabled_modules` derivation.
6. Add route access helper.
7. Add tests.
8. Apply helper to a small representative set of routes.

## Acceptance Criteria

- Documentation uses `GruhaMitra` consistently.
- README states current vs target clearly.
- No live frontend folders are touched.
- No secrets or local runtime files are copied.
- Tests describe tenant/module access expectations.
- The first PR can be reviewed without needing to understand a full frontend rewrite.
