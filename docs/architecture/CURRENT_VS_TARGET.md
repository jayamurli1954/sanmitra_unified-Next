# Current vs Target Matrix

This document prevents ambiguity during implementation. Treat current state as what can be relied on today from the reference backend. Treat target state as the direction to implement incrementally.

| Area | Current State | Target State | Foundation Gap |
| --- | --- | --- | --- |
| Workspace | Active work is in `D:\sanmitra_unified-Next`; reference backend is in `D:\sanmitra-backend` | All new unified work happens in `D:\sanmitra_unified-Next` | Copy/reference only what is needed; do not alter live/reference backend |
| Brands | Four unified brands are in scope: GruhaMitra, MandirMitra, MitraBooks, LegalMitra. InvestMitra is separate personal-use scope. | Unified backend and deployment cover GruhaMitra, MandirMitra, MitraBooks, and LegalMitra only | Normalize all new docs/code to `GruhaMitra` spelling and keep InvestMitra out of unified delivery plans |
| Frontends | Product frontend experiences are being consolidated for the four unified brands | Two deployable frontend experiences: MitraBooks Unified ERP and LegalMitra | Define API contract for menus/modules before merging UI |
| Backend | Unified FastAPI modular monolith exists in reference backend | Continue modular monolith | Add module registry and explicit module access checks |
| Accounting | Shared PostgreSQL accounting foundation exists | All accounting-heavy modules use shared accounting engine | Keep module logic from bypassing accounting service |
| MitraBooks business scope | Implemented but not production-ready for parties, typed vouchers, sales invoices, purchase bills, credit/debit notes, GST preparation, statements, bank reconciliation, inventory basics, fixed assets, dimensions, opening balances, and year-end close. Invoice/bill approval posting and compensation-reversal hardening are in place. | Business/professional workflows include parties, typed vouchers, sales, purchases, GST, inventory, AR/AP, MIS, data health, and exports | Use `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md` to phase scope, finish browser E2E/compliance/export depth, and reject desktop-era assumptions |
| Domain data | MongoDB domain data exists | MongoDB remains domain/operational store | Ensure every query is tenant-scoped |
| Product context | `X-App-Key` exists | Keep app key and add formal organization type | Do not collapse app key and organization type into one field |
| Tenancy | Tenant middleware/RBAC foundation exists | Tenant, organization type, enabled modules, role, and permissions drive access | Add `organization_type` and `enabled_modules` |
| Module access | Product routing exists, feature gating is not yet formalized | API and UI both use module registry | Add registry and test access decisions |
| Frontend merge | Not started in this workspace | Merge GruhaMitra, MandirMitra, and MitraBooks workflows into MitraBooks shell | First PR must prepare backend/docs only |

## Phase 1 Snapshot

- Implemented: shared accounting compensation/reversal protection now covers payroll, bulk import, typed vouchers, sales invoices, purchase bills, credit notes, debit notes, and GST settlement.
- Implemented: sales invoices and purchase bills now create as `draft` or `pending_approval` and post only on approval.
- Implemented: CA access no longer exposes plaintext or admin-visible temporary passwords; invite acceptance is token-based and the invited CA sets the password on first use.
- Implemented but not production-ready: the CA acceptance frontend UX, browser E2E, and wider CA practice model are still pending.
- Planned/deferred: attachment/document support, compliance signoff, export governance, Data Health Score, and advanced inventory/manufacturing depth.
