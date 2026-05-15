# Current vs Target Matrix

This document prevents ambiguity during implementation. Treat current state as what can be relied on today from the reference backend. Treat target state as the direction to implement incrementally.

| Area | Current State | Target State | Foundation Gap |
| --- | --- | --- | --- |
| Workspace | Active work is in `D:\sanmitra_unified-Next`; reference backend is in `D:\sanmitra-backend` | All new unified work happens in `D:\sanmitra_unified-Next` | Copy/reference only what is needed; do not alter live/reference backend |
| Brands | Five brands exist: GruhaMitra, MandirMitra, MitraBooks, LegalMitra, InvestMitra | Same five brands remain | Normalize all new docs/code to `GruhaMitra` spelling |
| Frontends | Five separate frontend experiences | Three frontend experiences: MitraBooks Unified ERP, LegalMitra, InvestMitra | Define API contract for menus/modules before merging UI |
| Backend | Unified FastAPI modular monolith exists in reference backend | Continue modular monolith | Add module registry and explicit module access checks |
| Accounting | Shared PostgreSQL accounting foundation exists | All accounting-heavy modules use shared accounting engine | Keep module logic from bypassing accounting service |
| Domain data | MongoDB domain data exists | MongoDB remains domain/operational store | Ensure every query is tenant-scoped |
| Product context | `X-App-Key` exists | Keep app key and add formal organization type | Do not collapse app key and organization type into one field |
| Tenancy | Tenant middleware/RBAC foundation exists | Tenant, organization type, enabled modules, role, and permissions drive access | Add `organization_type` and `enabled_modules` |
| Module access | Product routing exists, feature gating is not yet formalized | API and UI both use module registry | Add registry and test access decisions |
| Frontend merge | Not started in this workspace | Merge GruhaMitra, MandirMitra, and MitraBooks workflows into MitraBooks shell | First PR must prepare backend/docs only |

