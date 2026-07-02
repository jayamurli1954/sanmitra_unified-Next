# MitraBooks ERP Demo Credentials Runbook

## Purpose

This runbook records how the MitraBooks ERP demo admin is provisioned for staging and E2E validation. It intentionally does not record the actual password.

## Current State

MitraBooks ERP already has a demo bootstrap path in the backend:

- `DEMO_MITRABOOKS_BOOTSTRAP`
- `DEMO_MITRABOOKS_TENANT_ID`
- `DEMO_MITRABOOKS_ADMIN_EMAIL`
- `DEMO_MITRABOOKS_ADMIN_PASSWORD`
- `DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS`
- `DEMO_MITRABOOKS_E2E_SEED_ENABLED`

The password default is empty by design. It must be set only as a staging/runtime secret.

## Demo Tenant

| Field | Value |
| --- | --- |
| Staging URL | `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |
| Tenant id | `demo-mitrabooks-business` |
| App key | `mitrabooks` |
| Organization type | `BUSINESS` |
| Enabled modules | `business`, `accounting`, `gst`, `inventory`, `audit` |

## Demo Admin Identity

Use this as the operator-facing MitraBooks ERP demo admin email:

```text
business.admin@sanmitra.local
```

The backend also supports these aliases for the same demo tenant when configured:

```text
admin@mitrabooks.local
businessadmin@sanmitra.local
```

Do not commit, print, or paste the demo password into documentation, screenshots, test reports, or source code.

## Required Staging Backend Secrets

Set these on the staging backend service, not in the frontend and not in the repository:

```text
DEMO_MITRABOOKS_BOOTSTRAP=true
DEMO_MITRABOOKS_TENANT_ID=demo-mitrabooks-business
DEMO_MITRABOOKS_ADMIN_EMAIL=business.admin@sanmitra.local
DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS=admin@mitrabooks.local,businessadmin@sanmitra.local
DEMO_MITRABOOKS_ADMIN_PASSWORD=<staging-only secret>
DEMO_MITRABOOKS_E2E_SEED_ENABLED=true
```

The password must be generated and stored in the deployment secret manager. If the demo admin is not visible in staging, check these backend runtime variables first.

## Local Seed Option

For a local environment, seed the demo tenant with:

```powershell
$env:DEMO_MITRABOOKS_ADMIN_PASSWORD="<local-only password>"
python scripts/seed_mitrabooks_local_demo.py --tenant-id demo-mitrabooks-business --email business.admin@sanmitra.local --use-env-password
```

Use a local-only password. Do not reuse production, personal, or customer credentials.

## E2E Operator Variables

For the guarded destructive MitraBooks ERP staging gate, set these only in the operator shell/session:

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="business.admin@sanmitra.local"
$env:E2E_USER_PASSWORD="<same staging secret>"
```

Then run the non-mutating policy check first:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --destructive-demo-policy-check --demo-tenant-id demo-mitrabooks-business
```

Only after the demo tenant is reset/reseeded and the policy check passes, run:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

## Reset Policy

- Run destructive browser tests only against `demo-mitrabooks-business`.
- Never run destructive browser tests against customer, trust, housing society, CA practice, or production tenants.
- Reset or reseed the demo tenant before the destructive run.
- Reseed or discard the staging demo data after the destructive run.
- Keep the password in runtime secrets and operator environment only.

## Gap

The MitraBooks ERP demo credential path is documented and supported, but production readiness is not closed until the staging backend actually has the above secrets configured and an operator records the policy-check/destructive-run evidence in the Phase 3 signoff report.
