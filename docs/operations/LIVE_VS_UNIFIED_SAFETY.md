# Live-vs-Unified Safety and Pre-Production Gate

This is the platform-level safety doc for standing up the **unified SanMitra
backend** (`sanmitra_unified-Next`) alongside the **already-live MandirMitra and
GruhaMitra** apps. It answers one question: *can the unified backend run next to
the live apps without disturbing real users, real money, or real tenant data?*

It does not replace the per-app and per-process runbooks. It ties them together
and adds the checks that are specific to the live↔unified boundary:

- Release / rollback: [`RELEASE_AND_ROLLBACK.md`](./RELEASE_AND_ROLLBACK.md)
- Backup / restore: [`BACKUP_RESTORE_RUNBOOK.md`](./BACKUP_RESTORE_RUNBOOK.md)
- MandirMitra first-live signoff: [`MANDIRMITRA_PRODUCTION_SIGNOFF.md`](./MANDIRMITRA_PRODUCTION_SIGNOFF.md)
- Staged E2E sequence: [`STAGED_E2E_PLAN.md`](./STAGED_E2E_PLAN.md)

---

## 1. The two layers

There are two distinct layers in play. They must stay clearly separated until a
workflow is explicitly migrated.

| Layer | What it is | Rule |
| --- | --- | --- |
| **Live apps** | The MandirMitra and GruhaMitra production deployments serving real users today | Reference production. Do not disturb. Freeze current behavior as the baseline. |
| **Unified backend** | `sanmitra_unified-Next` — the shared ERP/accounting shell | Introduce carefully. Prove safe on staging/demo tenants before any real tenant touches it. |

The risk is **not** "live product risk." Both apps being live is good. The risk is
**migration/unification risk**: the unified backend connecting to live data, or a
real tenant being flipped into the unified shell, before isolation and rollback
are proven.

### Operator fill-in (confirm before any go-live)

The repo cannot assert these — the operator must record them:

| Question | Confirmed value |
| --- | --- |
| Live MandirMitra URL | _fill in_ |
| Live GruhaMitra URL | _fill in_ |
| Backend the live apps use today (old vs unified) | _fill in_ |
| Production database(s) name/location | _fill in_ |
| Is the unified backend connected to any production DB? | _fill in (must be No until migration)_ |
| Demo/seed tenants present in any production DB? | _fill in (must be No)_ |

---

## 2. What the code/config already enforces

These invariants are verifiable in the repo today and are covered by tests. They
do **not** need to be re-argued at each release — only confirmed not to have
regressed.

| Invariant | Where enforced | Test guard |
| --- | --- | --- |
| `tenant_id` comes only from the trusted JWT principal, never a request body/header | [`app/core/modules/dependencies.py`](../../app/core/modules/dependencies.py) | `tests/test_app_module_isolation_matrix.py::test_tenant_id_is_sourced_only_from_trusted_claims` |
| Cross-app access is denied (app_key + org_type + enabled_modules all checked) | [`app/core/modules/registry.py`](../../app/core/modules/registry.py) `require_module_access` | `tests/test_app_module_isolation_matrix.py` (full matrix) |
| Wrong `X-App-Key` is rejected / coerced to the default app key | [`app/core/tenants/context.py`](../../app/core/tenants/context.py) `resolve_app_key` | `tests/integration/test_app_key_aliases.py` |
| InvestMitra is excluded from the unified backend (no routes, no app key) | [`app/api/v1/router.py`](../../app/api/v1/router.py), [`app/config.py`](../../app/config.py) | `tests/test_app_module_isolation_matrix.py` (4 InvestMitra guards) |
| Health check treats PostgreSQL failure as hard error and MongoDB as degraded | [`app/main.py`](../../app/main.py) `/health` | — |
| Migrations run before traffic; tables are not auto-created in staging/prod | `render.yaml` `preDeployCommand: alembic upgrade head`, `PG_AUTO_CREATE_TABLES=false` | — |
| Debug OTP/email-link responses are blocked in production | [`app/config.py`](../../app/config.py) validation (`is_prod` raises) | — |

---

## 3. The `render.yaml` reality

The `render.yaml` in this repo defines **only the staging service**
(`sanmitra-unified-next-staging-sg`, `ENVIRONMENT=staging`). Production is a
separate Render service whose env vars are **not** in this file. Do not assume
production inherits staging values — each must be set on the production service.

`autoDeploy: true` on `main` is acceptable for staging. **Production must deploy
from a `backend-v*` tag with manual approval**, per `RELEASE_AND_ROLLBACK.md` — not
auto-deploy from branch head.

---

## 4. Demo / seed flag matrix

These flags drive startup seeding. The config layer
([`app/config.py`](../../app/config.py)) hard-errors in production when a flag is
on but its password is unset, **but it only logs a warning** when demo/bootstrap
flags are simply on in production with a password set. That means a misconfigured
production deploy can still seed demo data — so this is an **operator
responsibility**, not a hard gate.

| Flag | Staging (current) | Production (required) | Effect if left on |
| --- | --- | --- | --- |
| `SUPER_ADMIN_BOOTSTRAP` | `false` | `false` (or one-time, then off) | Re-creates/over-promotes a super admin on boot |
| `DEMO_MANDIR_BOOTSTRAP` | `false` | `false` | Seeds a demo temple tenant |
| `DEMO_MITRABOOKS_BOOTSTRAP` | `true` | **`false`** | Seeds a demo business tenant + admin into the DB |
| `DEMO_MITRABOOKS_E2E_SEED_ENABLED` | `true` | **`false`** | Seeds E2E fixture data into the DB |
| `AUTH_EMAIL_DEBUG_RETURN_LINK` | `false` | `false` | Returns auth links in API responses |
| `MOBILE_OTP_DEBUG_RETURN_CODE` | `false` | `false` | Returns OTP codes in API responses |

> The two **bold** flags are the most dangerous to carry into production: they
> write demo tenants/users into the live database. Confirm both are `false` on the
> production service before first real go-live.

---

## 5. Pre-production gate (run before flipping any real tenant)

A consolidated checklist. Items marked *(auto)* are guarded by tests/config; the
rest are operator confirmations.

**Scope & isolation**
- [ ] *(auto)* Tenant/app/module isolation matrix passes (`pytest tests/test_app_module_isolation_matrix.py`)
- [ ] *(auto)* InvestMitra excluded — no `/api/v1/investment` routes, app key not accepted
- [ ] No MandirMitra↔GruhaMitra data crossover possible (composite `tenant_id`+`app_key` scoping confirmed on the touched collections)
- [ ] `X-Tenant-ID` is not usable as a normal tenant switch; any super-admin override is explicit and audited

**Deployment safety**
- [ ] Production service env vars set explicitly (not inherited from staging)
- [ ] Production demo/seed flags all `false` (see §4)
- [ ] Production deploy references a `backend-v*` tag (not branch auto-deploy)
- [ ] `alembic upgrade head` runs pre-cutover; `PG_AUTO_CREATE_TABLES=false`
- [ ] `/health` returns healthy (PostgreSQL up); degraded-Mongo behavior understood

**Data safety**
- [ ] Unified backend is **not** pointed at any live production DB until migration is approved
- [ ] MongoDB + PostgreSQL backup schedule, retention, and restore owner confirmed (`BACKUP_RESTORE_RUNBOOK.md`)
- [ ] Restore procedure tested at least once
- [ ] No default/shared production passwords; no `.local` admin accounts in production

**Release discipline**
- [ ] CI green for the release commit/tag (compile, route contract, preflight)
- [ ] Rollback tag identified (previous known-good `backend-v*`)
- [ ] Post-deploy logs checked for config warnings (bootstrap flags, missing secrets)

---

## 6. Migration rule: one workflow at a time

Even though both live apps exist, **do not migrate both together**.

1. Keep live MandirMitra and GruhaMitra running, untouched, as the baseline.
2. Exercise MandirMitra workflows in unified **staging** against demo/test tenants.
3. Migrate selected MandirMitra workflows only after they pass.
4. Then exercise GruhaMitra workflows in unified staging.
5. Then migrate GruhaMitra.

This sequence matches `STAGED_E2E_PLAN.md` and avoids a combined failure surface.

---

## 7. Biggest practical risk: data confusion

The failure mode to design against is cross-context data leakage, e.g.:

- A MandirMitra donation posting into a GruhaMitra society ledger.
- A GruhaMitra maintenance receipt appearing in MandirMitra reports.
- A LegalMitra tenant reaching accounting routes.
- A demo tenant mixing with a real tenant.
- A public payment test hitting a real temple/trust record.

These are exactly the cases the isolation matrix in §2 guards. Tenant isolation,
app-key control, and module-access checks are more important than any new feature
until first live cut is accepted.
