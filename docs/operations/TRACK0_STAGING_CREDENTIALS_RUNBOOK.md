# Track 0 Staging Credentials Runbook

## Purpose

Track 0 is an ops-controlled credential parity gate for MitraBooks staging destructive E2E. This runbook defines how to rotate demo credentials safely, verify login context, and record evidence without committing secrets.

## Scope

- Applies to `demo-mitrabooks-business` staging validation only.
- Covers credential rotation, secret rollout, and auth precheck before destructive E2E.
- Does not allow storing plaintext credentials in repo files, screenshots, or CI logs.

Reference stage flow: `docs/operations/STAGED_E2E_PLAN.md` (Stage 2 MitraBooks ERP core and staged gating discipline).

## Required Staging Secrets

Configure these in staging secret manager/runtime only:

```text
JWT_SECRET=<64-byte random hex or stronger>
MANDIR_ONBOARDING_SECRET=<staging secret>
OTP_PEPPER=<staging secret>
DEMO_MITRABOOKS_BOOTSTRAP=true
DEMO_MITRABOOKS_TENANT_ID=demo-mitrabooks-business
DEMO_MITRABOOKS_ADMIN_EMAIL=business.admin@sanmitra.local
DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS=admin@mitrabooks.local,businessadmin@sanmitra.local
DEMO_MITRABOOKS_ADMIN_PASSWORD=<staging-only secret>
DEMO_MITRABOOKS_E2E_SEED_ENABLED=true
AUTH_EMAIL_DEBUG_RETURN_LINK=false
MOBILE_OTP_DEBUG_RETURN_CODE=false
SUPER_ADMIN_BOOTSTRAP=false
```

Notes:
- Keep `DEMO_MITRABOOKS_ADMIN_PASSWORD` and E2E operator password aligned.
- Never commit secret values to `.env`, docs, tests, or scripts.

## Rotation Procedure (Ops)

1. Generate a new staging-only demo password in the secret manager.
2. Update `DEMO_MITRABOOKS_ADMIN_PASSWORD` in staging backend secrets.
3. Confirm bootstrap flags and tenant identity values match this runbook.
4. Redeploy staging backend so runtime picks up new secrets.
5. Reseed/reset demo account mapping for `demo-mitrabooks-business`.
6. Share only operator instructions (not password) to test operator.

## Operator Session Setup (No Secret Commit)

Set variables only in operator shell:

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="business.admin@sanmitra.local"
$env:E2E_USER_PASSWORD="<staging-only password from secret manager>"
$env:STAGING_API_BASE_URL="https://sanmitra-unified-next-staging-sg.onrender.com"
```

## Read-Only Auth Verification Before Destructive E2E

Use the scripted verification. It does not print the access token or password.

```powershell
python scripts/verify_staging_auth.py
```

Script checks:
- login succeeds with `E2E_USER_EMAIL` + `E2E_USER_PASSWORD`
- token is issued
- `/api/v1/modules/me` resolves expected tenant/app context
- required module set includes `business`, `accounting`, `audit`

Expected:
- `tenant_id=demo-mitrabooks-business`
- `organization_type=BUSINESS`
- enabled modules include `business`, `accounting`, `audit`

Do not use a raw `curl` login response as signoff evidence because it prints the
access token to the terminal and may place credentials in shell history. The scripted
precheck intentionally emits only sanitized context.

## Credential-Free Hosted Checks

These checks are read-only and may run before Ops supplies the demo password:

```powershell
Invoke-RestMethod -Uri "https://sanmitra-unified-next-staging-sg.onrender.com/health" -Method Get
Invoke-WebRequest -Uri "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/" -Method Get -UseBasicParsing
```

They prove only that the staging API dependencies and frontend shell are reachable.
They do not prove demo-user login, tenant context, enabled modules, or mutation safety.

## Guarded Destructive E2E Sequence

1. Run the read-only credential and tenant-context verification:

```powershell
python scripts/verify_staging_auth.py
```

2. Run the non-mutating local policy check. This confirms the explicit tenant target,
confirmation marker, and required operator variables are present; it does not replace
the read-only hosted authentication verification above:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --destructive-demo-policy-check --demo-tenant-id demo-mitrabooks-business
```

3. Only after Ops confirms a fresh reset/reseed and both checks are green, run the
destructive gate. This command repeats authentication and tenant/module validation
immediately before Playwright starts any mutation:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

The destructive spec explicitly disables Playwright trace, video, and screenshots.
Do not remove that override: credential-bearing browser artifacts can capture login
request bodies or authenticated request headers.

4. Confirm reversals/cancellations completed, then have Ops reseed or discard generated
demo data if a clean baseline is required. A failed partial run must be treated as
requiring reset/reseed before retry.

5. Record sanitized evidence in
`docs/operations/MITRABOOKS_PHASE3_BUSINESS_WORKFLOW_SIGNOFF.md`. Never paste the
password, bearer token, or raw login response.

## Failure Handling

- `Invalid credentials`: rotate/reset demo password again, redeploy backend, reseed demo user, rerun `scripts/verify_staging_auth.py`.
- Wrong tenant context: correct demo seed mapping and alias emails, then reverify.
- Missing modules: re-enable tenant modules before any destructive run.

## Security Rules

- No plaintext secrets in repo, chat transcripts, test artifacts, or screenshots.
- No `.env` commits.
- No destructive E2E on non-demo tenants.
- Agents and operators must follow [AGENTS.md](../../AGENTS.md) §5 Agent Shell Command
  Guardrails before git, filesystem, database, deploy, or destructive-E2E shell commands.
  This repo uses policy-first guardrails instead of requiring external `destructive_command_guard`.
