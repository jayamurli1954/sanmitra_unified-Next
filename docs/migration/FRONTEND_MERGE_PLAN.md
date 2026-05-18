# Frontend Merge Plan

## Objective

Merge the accounting-heavy frontend experiences into a single MitraBooks Unified ERP shell while keeping LegalMitra and InvestMitra separate.

## Current Frontend Model

- GruhaMitra frontend.
- MandirMitra frontend.
- MitraBooks frontend.
- LegalMitra frontend.
- InvestMitra frontend.

## Target Frontend Model

- MitraBooks Unified ERP frontend:
  - GruhaMitra housing modules.
  - MandirMitra temple modules.
  - MitraBooks business/professional modules.
- LegalMitra frontend.
- InvestMitra frontend.

## Merge Sequence

### Phase 1: Backend Readiness

- `organization_type`.
- `enabled_modules`.
- Module registry.
- Feature/module access checks.
- `GET /api/v1/users/me` returns app, tenant, org type, enabled modules, and subscription plan.
- `GET /api/v1/modules/me` returns the frontend menu/module contract.

### Frontend Module Contract

The unified frontend should call:

```text
GET /api/v1/modules/me
```

Expected top-level response:

```json
{
  "tenant_id": "tenant-123",
  "app_key": "mitrabooks",
  "organization_type": "BUSINESS",
  "subscription_plan": "pro",
  "enabled_modules": [
    {
      "module_key": "accounting",
      "display_name": "MitraBooks Accounting Engine",
      "enabled": true,
      "minimum_plan": "free",
      "features": ["coa", "journal", "ledger", "reports"],
      "api_prefix": "/api/v1/accounting",
      "frontend_path": "/accounting",
      "nav_group": "Finance"
    }
  ],
  "available_modules": [],
  "navigation": [
    {
      "group_key": "finance",
      "display_name": "Finance",
      "items": [
        {
          "module_key": "accounting",
          "display_name": "MitraBooks Accounting Engine",
          "frontend_path": "/accounting",
          "api_prefix": "/api/v1/accounting"
        }
      ]
    }
  ]
}
```

Rules:

- Render navigation from `enabled_modules`.
- Use `available_modules` for locked/future modules only when the product wants to show upsell or disabled features.
- Do not hardcode product names to decide menus.
- Do not show trading actions for InvestMitra research modules.
- Do not show LegalMitra AI assistant unless `legal_ai` is enabled.

## Unified Shell Contract v1

The frontend shell should use `navigation` as its primary menu source.

Navigation group order:

1. Operations
2. Portfolio
3. Finance
4. Compliance
5. Legal
6. Research
7. AI Assistant
8. Administration

Expected module-to-menu mapping:

| Module | Group | Notes |
| --- | --- | --- |
| `housing` | Operations | GruhaMitra housing workflows |
| `temple` | Operations | MandirMitra temple workflows |
| `business` | Operations | MitraBooks business workflows |
| `professional` | Operations | MitraBooks professional workflows |
| `inventory` | Operations | Business inventory |
| `accounting` | Finance | Shared accounting engine |
| `billing` | Finance | Professional/client billing |
| `gst` | Compliance | GST and tax workflow |
| `compliance` | Compliance | LegalMitra compliance |
| `legal` | Legal | Legal cases/documents |
| `rag` | Legal | Legal research |
| `investment` | Portfolio | Holdings and asset classes |
| `portfolio` | Portfolio | Portfolio analytics |
| `investment_research` | Research | FinceptTerminal research, disabled by default |
| `broker_research` | Research | Zerodha Kite MCP read-only research, disabled by default |
| `legal_ai` | AI Assistant | Claude for Legal, disabled by default |
| `audit` | Administration | Audit trail |

The frontend must treat `enabled_modules` as executable/visible and `available_modules` as locked/future. A locked module must not expose working routes unless backend access is enabled.

### Phase 2: Unified Shell

- Create MitraBooks shell layout.
- Dynamic navigation from API module list.
- Shared accounting dashboard.
- Shared settings/profile/tenant switch where applicable.

### Phase 3: Module Migration

Migrate one module at a time:

1. MitraBooks accounting/business base.
2. MandirMitra temple module.
3. GruhaMitra housing module.

Do not migrate all screens in one PR.

## Staged E2E Gates

E2E validation must be completed stage by stage so troubleshooting stays manageable for a one-person platform owner.

Required order:

1. LegalMitra baseline: confirm the tested and deployed live product has no regression.
2. MitraBooks ERP core: validate accounting, tenant context, module registry, navigation, reports, RBAC, and idempotency.
3. MandirMitra in MitraBooks ERP: validate donations, receipts, seva booking, devotees, and accounting posting.
4. GruhaMitra in MitraBooks ERP: validate flats/residents, maintenance billing, collections, complaints where implemented, and accounting posting.
5. Combined MitraBooks ERP regression: validate MitraBooks, MandirMitra, and GruhaMitra together with module access and accounting invariants.
6. InvestMitra: validate portfolio, P&L, analytics, and read-only research integrations after ERP is stable.

Do not expand to a later stage until the previous stage has a passing smoke/E2E checklist or a documented exception.

### Phase 4: Legacy Compatibility

- Keep old URLs or redirects where needed.
- Keep app-key compatibility.
- Avoid breaking live deployments until the unified frontend is tested.

## Design Rule

The frontend must be feature-driven, not product-hardcoded.

Bad:

```text
if product == "mandirmitra" show sevas
```

Better:

```text
if enabled_modules includes "temple" and permissions include "seva:read" show sevas
```
