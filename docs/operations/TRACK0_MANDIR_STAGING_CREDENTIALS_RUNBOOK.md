# Track 0 MandirMitra Staging Credentials Runbook

## Purpose

Add-on Track 0 gate for MandirMitra Stage 3 hosted staging destructive E2E. Use this when Ops enables the staging demo temple tenant; do not rewrite or replace `docs/operations/TRACK0_STAGING_CREDENTIALS_RUNBOOK.md` (MitraBooks).

This runbook defines staging secret enablement, auth precheck, maker provisioning, and guarded destructive commands without committing secrets.

## Scope

- Applies only to an explicit demo/test/seed Mandir tenant on hosted staging.
- **Chosen demo workspace (2026-07-15):** **Demo Temple** in Platform Owners (likely **temple id `1`** in the ID column).
- **Important:** Platform Owners **ID** is numeric `temple_id` (1, 2, 3…). Destructive E2E and auth gates use the string **`tenant_id`** from `/api/v1/modules/me` (for example `demo-mandir-tenant` or `demo-temple`). Never pass `1` as `--tenant-id`.
- Covers credential rotation, Render secret rollout, `platform_can_write` precheck, and dual-actor auth before destructive E2E.
- Never mutate Parlathya Prathishtana or any real trust/temple tenant.
- Does not allow storing plaintext credentials in repo files, screenshots, traces, or CI logs.

Cross-links:

- Checklist: `docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md`
- Signoff: `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md`
- MitraBooks Track 0 (unchanged): `docs/operations/TRACK0_STAGING_CREDENTIALS_RUNBOOK.md`
- Stage flow: `docs/operations/STAGED_E2E_PLAN.md` (Stage 3 MandirMitra)

## Current State vs Enablement Path

| Item | Current state | Enablement target |
| --- | --- | --- |
| Platform owner UI | Hosted Mandir lists **Demo Editable** temples (not Parlathaya). Use those for gated mutation, never the real trust. | Confirm exact `tenant_id`, two `tenant_admin` logins, and `/temples/current.platform_can_write=true` before destructive E2E |
| `DEMO_MANDIR_BOOTSTRAP` in staging `render.yaml` | `false` (auto-seed on deploy is off) | Optional: set `true` on staging only if Ops wants Render startup to recreate/reset a known demo tenant every deploy |
| Hosted destructive Stage 3 | PASS (2026-07-17): 8/8 on Demo Temple `demo-mandir-tenant` with dual `tenant_admin` actors; evidence `tmp/mandir-stage3-destructive-evidence.json` | Re-run after Track 0 Mandir auth precheck if staging demo is reseeded or credentials rotate |

**Correction:** “`DEMO_MANDIR_BOOTSTRAP=false`” means Render does **not** auto-bootstrap a Mandir demo at deploy time. It does **not** mean demo temples are absent. Platform ops can still show **Demo Editable** temples (for example “MandirMitra Temple - Demo” and “Demo Temple”). Those are valid destructive targets once their machine `tenant_id` and operator passwords are known. Parlathaya Prathishtana remains **read-only / real** and must never be used for Stage 3 mutation.

This file is the enablement path for credentials and precheck. Prefer an existing Demo Editable workspace if Ops already has logins; only flip bootstrap if you need automated reseed on every staging deploy.

## Required Staging Secrets (Render)

Configure in staging secret manager / Render env only. Do not put values in git.

```text
DEMO_MANDIR_BOOTSTRAP=true
DEMO_MANDIR_TENANT_ID=demo-mandir-tenant
DEMO_MANDIR_ADMIN_EMAIL=<staging-only demo admin email>
DEMO_MANDIR_ADMIN_PASSWORD=<staging-only secret>
DEMO_MANDIR_TEMPLE_NAME=<demo temple name>
DEMO_MANDIR_TRUST_NAME=<demo trust name>
DEMO_MANDIR_UPI_ID=<demo-only UPI id, never a real trust UPI>
DEMO_MANDIR_UPI_PAYEE_NAME=<demo-only payee name>
AUTH_EMAIL_DEBUG_RETURN_LINK=false
MOBILE_OTP_DEBUG_RETURN_CODE=false
SUPER_ADMIN_BOOTSTRAP=false
```

Notes:

- Bootstrap creates the demo temple admin only. Stage 3 destructive E2E requires a second distinct `tenant_admin` maker on the same demo tenant. Provision that maker separately after bootstrap (Ops user create / approved seed helper). Approver and maker emails and passwords must differ.
- Demo UPI/payee values must never mirror Parlathya or live trust accounts.
- Keep `DEMO_MANDIR_BOOTSTRAP=false` in production. Staging `render.yaml` ships `false` until Ops intentionally enables this path.
- Never commit secret values to `.env`, docs, tests, or scripts.

## Hosted Targets

| Role | URL |
| --- | --- |
| Frontend (MitraBooks ERP shell) | `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |
| Staging API | `https://sanmitra-unified-next-staging-sg.onrender.com` |

Confirmation string format (launcher builds this; operators must understand the contract):

```text
DESTROY_DEMO_ONLY:<demo-tenant-id>@<api-origin>
```

Example for the recommended tenant and staging API:

```text
DESTROY_DEMO_ONLY:demo-mandir-tenant@https://sanmitra-unified-next-staging-sg.onrender.com
```

## Rotation Procedure (Ops)

1. Generate a new staging-only demo admin password in the secret manager.
2. Update `DEMO_MANDIR_ADMIN_PASSWORD` (and email if rotated) in Render staging.
3. Confirm `DEMO_MANDIR_BOOTSTRAP=true`, `DEMO_MANDIR_TENANT_ID=demo-mandir-tenant`, and demo UPI values.
4. Redeploy staging backend so bootstrap applies.
5. Provision or reset the second distinct maker `tenant_admin` on `demo-mandir-tenant`.
6. Confirm `/temples/current` for that tenant reports `platform_can_write=true`.
7. Share only operator instructions (not passwords) to the test operator.

## Operator Session Setup (No Secret Commit)

Set variables only in the operator shell:

```powershell
$env:STAGING_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:STAGING_APP_KEY = "mandirmitra"
$env:EXPECTED_TENANT_ID = "demo-mandir-tenant"
$env:E2E_USER_EMAIL = "<staging demo admin email>"
$env:E2E_USER_PASSWORD = "<staging-only password from secret manager>"
$env:MANDIRMITRA_SMOKE_EMAIL = $env:E2E_USER_EMAIL
$env:MANDIRMITRA_SMOKE_PASSWORD = $env:E2E_USER_PASSWORD
```

### Create Demo Temple `tenant_admin` (when Super Admin only has UI switcher access)

If you are logged in as `superadmin@sanmitra.local` and only see Demo Temple via Platform Owners / temple switcher, create a real Demo Temple admin (does not print passwords):

```powershell
$env:STAGING_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:STAGING_APP_KEY = "mandirmitra"
$env:MANDIR_DEMO_TEMPLE_ID = "1"   # Platform Owners ID for Demo Temple
$env:MANDIR_DEMO_ADMIN_EMAIL = "temple.demo.admin@sanmitratech.in"

python scripts\provision_mandir_demo_tenant_admin.py
```

Notes:

- Do **not** use `@sanmitra.local` for `POST /api/v1/users` — staging EmailStr validation rejects `.local` as a reserved domain (HTTP 422). Use `@sanmitratech.in` or another real domain.
- Super Admin login with `@sanmitra.local` can still work; only the **create-user** schema is strict.

## Read-Only Auth Verification Before Destructive E2E

Preferred scripted precheck (does not print the access token):

```powershell
$env:STAGING_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:STAGING_APP_KEY = "mandirmitra"
$env:EXPECTED_TENANT_ID = "demo-mandir-tenant"   # placeholder until precheck prints the real value
$env:E2E_USER_EMAIL = "temple.demo@sanmitra.local"  # or demo.admin@sanmitra.local — use the login Ops gave you
$env:E2E_USER_PASSWORD = "<staging-only password from Render secret manager>"

python scripts\verify_mandir_staging_auth.py
```

Expect: `PASS`, a string `tenant_id` containing `demo`, `test`, or `seed`, `temple_id=1` (if Demo Temple is the first onboarded temple), `organization_type=TEMPLE`, `platform_can_write=True`.

Use the printed **`tenant_id`** (not temple id `1`) for `--tenant-id` and `MANDIRMITRA_DEMO_E2E_CONFIRM`.

Legacy PowerShell precheck (same checks) remains below if the script is unavailable.

```powershell
$api = $env:STAGING_API_BASE_URL.TrimEnd('/')
$email = $env:E2E_USER_EMAIL
$password = $env:E2E_USER_PASSWORD
$expectedTenant = $env:EXPECTED_TENANT_ID
$login = Invoke-RestMethod -Method Post -Uri "$api/api/v1/auth/login" `
  -Headers @{ "Content-Type" = "application/json"; "X-App-Key" = "mandirmitra" } `
  -Body (@{ email = $email; password = $password } | ConvertTo-Json)
if (-not $login.access_token) { throw "FAIL: no access token" }
$token = $login.access_token
$me = Invoke-RestMethod -Method Get -Uri "$api/api/v1/modules/me" `
  -Headers @{ Authorization = "Bearer $token"; "X-App-Key" = "mandirmitra" }
$temple = Invoke-RestMethod -Method Get -Uri "$api/api/v1/temples/current" `
  -Headers @{ Authorization = "Bearer $token"; "X-App-Key" = "mandirmitra" }
Remove-Variable token, login -ErrorAction SilentlyContinue
$modules = @($me.enabled_modules | ForEach-Object { $_.module_key })
$errors = @()
if ($me.tenant_id -ne $expectedTenant) { $errors += "tenant mismatch: $($me.tenant_id)" }
if ($me.organization_type -ne "TEMPLE") { $errors += "organization_type=$($me.organization_type)" }
foreach ($m in @("temple", "accounting", "audit")) {
  if ($modules -notcontains $m) { $errors += "missing module: $m" }
}
if (-not $temple.platform_can_write) { $errors += "platform_can_write is not true" }
if ($errors.Count) { $errors | ForEach-Object { "FAIL: $_" }; exit 1 }
Write-Host "PASS: Mandir staging auth context verified"
Write-Host " - tenant_id=$($me.tenant_id)"
Write-Host " - organization_type=$($me.organization_type)"
Write-Host " - platform_can_write=$($temple.platform_can_write)"
Write-Host " - modules=$([string]::Join(',', $modules))"
```

Expected:

- `tenant_id=demo-mandir-tenant` (or the explicit demo id Ops enabled)
- `organization_type=TEMPLE`
- enabled modules include `temple`, `accounting`, `audit`
- `platform_can_write=true`

Repeat a shortened login/`modules/me` check for the maker email as well (distinct user, same tenant). Do not paste tokens into evidence.

## Credential-Free Hosted Checks

```powershell
Invoke-RestMethod -Uri "https://sanmitra-unified-next-staging-sg.onrender.com/health" -Method Get
Invoke-WebRequest -Uri "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/" -Method Get -UseBasicParsing
```

These prove reachability only. They do not prove demo login, TEMPLE context, `platform_can_write`, or mutation safety.

## Non-Destructive Browser Smoke (After Auth PASS)

```powershell
python scripts\mandirmitra_stage3_browser_smoke.py `
  --api-base "https://sanmitra-unified-next-staging-sg.onrender.com" `
  --frontend-url "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/"
```

Password comes from `MANDIRMITRA_SMOKE_PASSWORD` only. Evidence under `tmp\` must stay sanitized.

## Guarded Destructive E2E Sequence

Hosts:

- Frontend: `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`
- API: `https://sanmitra-unified-next-staging-sg.onrender.com`

1. Complete the Mandir auth + `platform_can_write` precheck above for admin (approver) and maker.

2. Dry-run (no services contacted, no data changed):

```powershell
python scripts\run_mandirmitra_stage3_destructive.py `
  --frontend-url "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/" `
  --api-base-url "https://sanmitra-unified-next-staging-sg.onrender.com" `
  --tenant-id "demo-mandir-tenant" `
  --approver-email "<staging demo admin email>" `
  --maker-email "<staging distinct maker email>"
```

Expected: `READY: static destructive-gate inputs are valid...`

3. Only after Ops confirms a fresh reset/reseed and the dry-run is green, execute. Passwords are prompted without echo; never pass them on the command line:

```powershell
python scripts\run_mandirmitra_stage3_destructive.py `
  --frontend-url "https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/" `
  --api-base-url "https://sanmitra-unified-next-staging-sg.onrender.com" `
  --tenant-id "demo-mandir-tenant" `
  --approver-email "<staging demo admin email>" `
  --maker-email "<staging distinct maker email>" `
  --execute
```

When prompted, type `demo-mandir-tenant`, then approver and maker passwords. The child suite expects confirmation  
`DESTROY_DEMO_ONLY:demo-mandir-tenant@https://sanmitra-unified-next-staging-sg.onrender.com`.

Playwright trace, video, and screenshots stay disabled for this suite. Do not re-enable them: credential-bearing artifacts can capture login bodies or auth headers.

4. Confirm reversals/cancellations completed, then reseed or discard generated demo data. A failed partial run requires reset/reseed before retry.

5. Record sanitized evidence per `docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md` and `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md`. Never paste passwords, bearer tokens, or raw login responses.

## Failure Handling

- `Invalid credentials`: rotate/reset demo password in Render, redeploy, reseed admin/maker, rerun auth precheck.
- Wrong tenant or `organization_type` not `TEMPLE`: fix `DEMO_MANDIR_*` identity mapping and bootstrap, redeploy, reverify.
- `platform_can_write` false: stop; do not run `--execute`. Confirm bootstrap wrote the demo temple write marker or Ops fixed the temple record for `demo-mandir-tenant` only.
- Identical approver/maker: provision a second distinct `tenant_admin` on the same demo tenant.
- Real trust selected (e.g. Parlathya): abort. Destructive E2E is demo-tenant only.

## Security Rules

- No plaintext secrets in repo, chat transcripts, test artifacts, or screenshots.
- No `.env` commits.
- No destructive E2E on non-demo tenants; never on Parlathya or live trusts.
- Traces/videos off for destructive Mandir Stage 3.
- Reseed after every destructive run (pass or fail with partial mutation).
- Agents and operators must follow [AGENTS.md](../../AGENTS.md) §5 Agent Shell Command Guardrails before git, filesystem, database, deploy, or destructive-E2E shell commands.
