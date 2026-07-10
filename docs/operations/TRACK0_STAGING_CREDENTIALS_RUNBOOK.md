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

Use either the script or curl-style calls.

### Option A: Scripted verification (preferred)

```powershell
python scripts/verify_staging_auth.py
```

Script checks:
- login succeeds with `E2E_USER_EMAIL` + `E2E_USER_PASSWORD`
- token is issued
- `/api/v1/modules/me` resolves expected tenant/app context
- required module set includes `business`, `accounting`, `audit`

### Option B: Manual curl verification

```bash
curl -sS -X POST "$STAGING_API_BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-App-Key: mitrabooks" \
  -d '{"email":"'"$E2E_USER_EMAIL"'","password":"'"$E2E_USER_PASSWORD"'"}'
```

Then call:

```bash
curl -sS "$STAGING_API_BASE_URL/api/v1/modules/me" \
  -H "Authorization: Bearer <access_token_from_login>" \
  -H "X-App-Key: mitrabooks"
```

Expected:
- `tenant_id=demo-mitrabooks-business`
- `organization_type=BUSINESS`
- enabled modules include `business`, `accounting`, `audit`

## Guarded Destructive E2E Sequence

1. Run policy/auth precheck first:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --destructive-demo-policy-check --demo-tenant-id demo-mitrabooks-business
```

2. Only if precheck is green, run destructive gate:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

3. Record evidence in `docs/operations/MITRABOOKS_PHASE3_BUSINESS_WORKFLOW_SIGNOFF.md`.

## Failure Handling

- `Invalid credentials`: rotate/reset demo password again, redeploy backend, reseed demo user, rerun `scripts/verify_staging_auth.py`.
- Wrong tenant context: correct demo seed mapping and alias emails, then reverify.
- Missing modules: re-enable tenant modules before any destructive run.

## Security Rules

- No plaintext secrets in repo, chat transcripts, test artifacts, or screenshots.
- No `.env` commits.
- No destructive E2E on non-demo tenants.
