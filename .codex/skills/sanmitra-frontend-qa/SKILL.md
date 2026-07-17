---
name: sanmitra-frontend-qa
description: SanMitra frontend QA workflow for MitraBooks ERP, LegalMitra, GruhaMitra, MandirMitra, route contracts, permissions-driven navigation, responsive behavior, visual regressions, workflow ergonomics, Playwright/smoke checks, and frontend preflight readiness.
---

# SanMitra Frontend QA

## Authority

- Treat `AGENTS.md` as mandatory policy and source of truth.
- Do not merge all frontends in one step.
- Keep LegalMitra separate from the MitraBooks ERP frontend unless the platform owner explicitly changes that direction.
- Keep InvestMitra out of unified frontend deployment scope.
- Load domain skills when the UI touches tenant, accounting, legal, MandirMitra, GruhaMitra, MitraBooks, or migration behavior.

## QA Focus

1. Identify the user workflow and product context: MitraBooks ERP, LegalMitra, MandirMitra, or GruhaMitra.
2. Check the UI is driven by enabled modules and permissions, not hardcoded product assumptions.
3. Check route contracts, API headers, `Authorization`, `X-App-Key`, and tenant-safe behavior.
4. Check critical workflows: navigation, create/edit/save, validation errors, loading states, empty states, permission-denied states, and failed API calls.
5. Check responsive layout, text fit, overlapping UI, and scanner-friendly operational density.

## Design Guardrails

- Use practical workflow screens, not marketing-style pages, for operational tools.
- Keep controls familiar: icons for actions, toggles for binary state, tabs for views, inputs for numeric values, menus for option sets.
- Avoid nested cards, decorative gradients, oversized hero treatment, and one-note palettes in ERP/operational UI.
- Ensure text fits within controls on mobile and desktop.
- Preserve stable dimensions for grids, boards, counters, tables, and toolbars.

## Validation

- For frontend changes, run or require `python scripts/preflight.py --frontend` before commit/push.
- Use screenshots or Playwright checks for visual or workflow-risk changes when practical.
- State any untested browser, viewport, route, permission, or API-contract risk.
